from .models import Transaction
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework import status
from rest_framework.response import Response
import requests
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import hashlib
import hmac
import json
from .serializers import DepositSerializer
from .throttling import PaymentInitThrottle
import os
from drf_yasg.utils import swagger_auto_schema
from Account.models import User
from django.utils import timezone
from logs.models import LogEntry
from django.db import transaction as db_transaction
from decimal import Decimal
import uuid

@swagger_auto_schema(methods=['POST'], request_body=DepositSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentInitThrottle])  # Rate limit: 5 requests per minute

def initialize_deposit(request):
    user = request.user
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = Decimal(str(serializer.validated_data['amount']))  # Use Decimal for precision
    email = serializer.validated_data['email']

    if user.email != email:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='404',
            message='Email address does not match at Payment/initialize_deposit',
            user=user
        )
        return Response({'message': 'email address not valid'}, status=status.HTTP_404_NOT_FOUND)
    
    # IDEMPOTENCY: Check for recent pending transactions to prevent duplicates
    recent_pending = Transaction.objects.filter(
        user=user,
        amount_paid=amount,
        completed=False,
        date_created__gte=timezone.now() - timezone.timedelta(minutes=10)
    ).first()
    
    if recent_pending:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Info',
            status_code='200',
            message=f'Returning existing pending transaction for {user.email}',
            user=user
        )
        return Response({
            'message': 'Transaction already initiated',
            'reference': recent_pending.reference
        }, status=status.HTTP_200_OK)
    
    # Generate unique reference for idempotency
    unique_ref = f"SocraSeek_{user.id}_{int(timezone.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {"authorization": f"Bearer {os.getenv('PRIVATE_KEY')}"}
    request_body = {
        'amount': int(amount * 100),
        'email': email,
        'reference': unique_ref,  # Use our generated reference for idempotency
    }
    
    try:
        r = requests.post(url, headers=headers, json=request_body)
        r.raise_for_status()
        response = r.json()
        
        Transaction.objects.create(
            user=user,
            type_of_transaction='Payment',
            date_created=timezone.now(),
            amount_paid=amount,
            reference=response['data']['reference'],
            completed=False
        )
        
        data = {
            'message': 'Transaction initiated.',
            'data': response
        }
        return Response(data, status=status.HTTP_200_OK)
        
    except requests.exceptions.RequestException as e:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Paystack API error: {str(e)}',
            user=user
        )
        return Response({'error': 'Payment initialization failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@require_POST
@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Paystack webhook to handle payment events
    """
    paystack_secret = os.getenv('PRIVATE_KEY')
    signature = request.headers.get('x-paystack-signature')
    
    # Log webhook receipt
    LogEntry.objects.create(
        timestamp=timezone.now(),
        level='INFO',
        status_code='200',
        message=f'Webhook received: {request.headers}',
    )
    
    if not signature:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='400',
            message='No signature at Payment/paystack_webhook',
        )
        return Response({'error': 'No signature'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify signature
    body = request.body.decode('utf-8')
    computed_signature = hmac.new(
        paystack_secret.encode('utf-8'),
        body.encode('utf-8'),
        digestmod=hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(computed_signature, signature):
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='400',
            message='Invalid signature at Payment/paystack_webhook',
        )
        return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse the webhook payload
    try:
        payload = json.loads(body)
        # SECURITY: Log only safe fields, not sensitive customer data
        safe_log = {
            'event': payload.get('event'),
            'reference': payload.get('data', {}).get('reference'),
            'status': payload.get('data', {}).get('status'),
        }
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='INFO',
            status_code='200',
            message=f'Webhook event: {safe_log["event"]}, ref: {safe_log["reference"]}',
        )
    except json.JSONDecodeError:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='400',
            message='Invalid JSON at Payment/paystack_webhook',
        )
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
    
    event = payload.get('event')
    data = payload.get('data')
    
    # Log the event
    LogEntry.objects.create(
        timestamp=timezone.now(),
        level='INFO',
        status_code='200',
        message=f'Processing webhook event: {event}',
    )
    
    # Handle different events
    if event == 'charge.success':
        return handle_successful_payment(data)
    elif event == 'charge.failed':
        return handle_failed_payment(data)
    else:
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Warning',
            status_code='200',
            message=f'Unhandled webhook event: {event}',
        )
        return Response({'status': 'unhandled_event'}, status=status.HTTP_200_OK)

def handle_successful_payment(data):
    """
    Handle successful payment webhook
    """
    from Account.utils import is_student_email
    
    # Valid plan amounts (using Decimal for precision)
    STUDENT_PLAN_AMOUNT = Decimal('3000.00')
    PREMIUM_PLAN_AMOUNT = Decimal('7500.00')
    
    reference = data.get('reference')
    
    # CRITICAL: Use database transaction with locking to prevent race conditions
    try:
        with db_transaction.atomic():
            # Use select_for_update() to lock the row until transaction completes
            # This prevents duplicate webhook processing
            transaction = Transaction.objects.select_for_update().get(
                reference=reference,
                completed=False
            )
            
            # Get payment details from our database
            db_amount = Decimal(str(transaction.amount_paid))
            user = transaction.user
            
            # SECURITY: Verify Paystack amount matches our database amount
            paystack_amount_kobo = data.get('amount', 0)
            paystack_amount = Decimal(str(paystack_amount_kobo)) / Decimal('100')  # Convert from kobo to naira
            
            # Allow small tolerance for rounding (1 kobo = 0.01 naira)
            if abs(paystack_amount - db_amount) > Decimal('0.01'):
                transaction.completed = True
                transaction.date_completed = timezone.now()
                transaction.save()
                
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Error',
                    status_code='400',
                    message=f'SECURITY: Amount mismatch! DB: {db_amount}, Paystack: {paystack_amount}. '
                            f'Reference: {reference}. Access denied.'
                )
                
                return Response({
                    'status': 'amount_mismatch',
                    'message': 'Payment amount verification failed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            amount = db_amount  # Use verified amount
        
            # CRITICAL: Validate that the amount is exactly one of the valid plan amounts
            if amount not in [STUDENT_PLAN_AMOUNT, PREMIUM_PLAN_AMOUNT]:
                # Invalid amount - mark transaction as completed but don't grant access
                transaction.completed = True
                transaction.date_completed = timezone.now()
                transaction.save()
                
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Error',
                    status_code='400',
                    message=f'SECURITY: Invalid payment amount {amount} from {user.email}. '
                            f'Only {STUDENT_PLAN_AMOUNT} (student) or {PREMIUM_PLAN_AMOUNT} (premium) allowed. '
                            f'Access denied. Reference: {reference}'
                )
                
                return Response({
                    'status': 'invalid_amount',
                    'message': f'Invalid payment amount. Only {STUDENT_PLAN_AMOUNT} or {PREMIUM_PLAN_AMOUNT} are valid.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Handle Student Plan (3000)
            if amount == STUDENT_PLAN_AMOUNT:
                # Verify user has student email
                if not is_student_email(user.email):
                    # Reject - student plan requires student email
                    transaction.completed = True
                    transaction.date_completed = timezone.now()
                    transaction.save()
                    
                    LogEntry.objects.create(
                        user=user,
                        timestamp=timezone.now(),
                        level='Error',
                        status_code='403',
                        message=f'SECURITY: Student plan payment rejected for non-student email {user.email}. '
                                f'Amount: {amount}. Access denied. Reference: {reference}'
                    )
                    
                    return Response({
                        'status': 'student_email_required',
                        'message': 'Student plan requires a student/educational email address.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Grant student subscription
                user.user_type = 'student'
                user.premium_user = True
                user.subscription_end_date = timezone.now().date() + timezone.timedelta(days=30)
                user.save()
                
                # Mark transaction as completed
                transaction.completed = True
                transaction.date_completed = timezone.now()
                transaction.save()
                
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Normal',
                    status_code='200',
                    message=f'Student subscription activated for {user.email}. Amount: {amount}. Reference: {reference}'
                )
                
                return Response({'status': 'success', 'plan': 'student'}, status=status.HTTP_200_OK)
            
            # Handle Premium Plan (7500)
            elif amount == PREMIUM_PLAN_AMOUNT:
                # Grant premium subscription (available to everyone)
                user.user_type = 'premium'
                user.premium_user = True
                user.subscription_end_date = timezone.now().date() + timezone.timedelta(days=30)
                user.save()
                
                # Mark transaction as completed
                transaction.completed = True
                transaction.date_completed = timezone.now()
                transaction.save()
                
                LogEntry.objects.create(
                    user=user,
                    timestamp=timezone.now(),
                    level='Normal',
                    status_code='200',
                    message=f'Premium subscription activated for {user.email}. Amount: {amount}. Reference: {reference}'
                )
                
                return Response({'status': 'success', 'plan': 'premium'}, status=status.HTTP_200_OK)
        
    except Transaction.DoesNotExist:
        # Log this for investigation
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='404',
            message=f'No Transaction for {reference} at Payment/paystack_webhook',
        )
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Log the error for investigation
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'{str(e)} at Payment/paystack_webhook',
        )
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def handle_failed_payment(data):
    """
    Handle failed payment webhook
    """
    reference = data.get('reference')
    
    try:
        transaction = Transaction.objects.get(reference=reference)
        transaction.completed = False
        transaction.save()
        LogEntry.objects.create(
        timestamp = timezone.now(),
        level = 'Normal',
        status_code = '200',
        message = 'Failed Payment at Payment/paystack_webhook',
        )
        
        return Response({'status': 'failed_handled'}, status=status.HTTP_200_OK)
        
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-date_created')
    data = []
    for tx in transactions:
        data.append({
            'type_of_transaction': tx.type_of_transaction,
            'date_created': tx.date_created,
            'amount_paid': tx.amount_paid,
            'reference': tx.reference,
            'completed': tx.completed,
            'date_completed': tx.date_completed,
        })
    return Response({'transactions': data}, status=status.HTTP_200_OK)