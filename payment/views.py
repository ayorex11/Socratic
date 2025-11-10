from .models import Transaction
from rest_framework.decorators import api_view, permission_classes
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
import os
from drf_yasg.utils import swagger_auto_schema
from Account.models import User
from django.utils import timezone
from logs.models import LogEntry

@swagger_auto_schema(methods=['POST'], request_body=DepositSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])

def initialize_deposit(request):
    user = request.user
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']
    email = serializer.validated_data['email']

 
    if user.email != email:
        LogEntry.objects.create(
        timestamp = timezone.now(),
        level = 'Error',
        status_code = '404',
        message = 'Email address does not match at Payment/initialize_deposit',
        user = user
        )
        return Response({'message': 'email address not valid'}, status=status.HTTP_404_NOT_FOUND)
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {"authorization": f"Bearer {os.getenv('PRIVATE_KEY')}"}
    request_body = {
        'amount' : int(amount * 100),
        'email' : email,
    }
    r = requests.post(url, headers=headers, json=request_body)
    r.raise_for_status()
    response = r.json()
    
    Transaction.objects.create(
        user = user,
        type_of_transaction = 'Payment',
        date_created = timezone.now(),
        amount_paid = amount,
        reference = response['data']['reference'],
        completed = False
    )
    data = {'message': 'Transaction initiated.',
            'data': response}
    
    return Response(data, status=status.HTTP_200_OK)

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
        # Log the payload for debugging
        LogEntry.objects.create(
            timestamp=timezone.now(),
            level='INFO',
            status_code='200',
            message=f'Webhook payload: {json.dumps(payload)}',
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
    reference = data.get('reference')


    
    try:
        # Find the transaction
        transaction = Transaction.objects.get(
            reference=reference,
            completed=False
        )
        
        # Update transaction status
        transaction.completed = True
        transaction.date_completed = timezone.now()
        transaction.save()
        transaction.user.premium_user = True
        transaction.user.subscription_end_date = timezone.now() + timezone.timedelta(days=30)
        transaction.user.save()
        

        
        

        
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
    except Transaction.DoesNotExist:
        # Log this for investigation
        print(f"Transaction with reference {reference} not found")
        LogEntry.objects.create(
        timestamp = timezone.now(),
        level = 'Error',
        status_code = '404',
        message = f'No Transaction for {reference} at Payment/paystack_webhook',
        )
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Log the error for investigation
        print(f"Error processing webhook: {str(e)}")
        LogEntry.objects.create(
        timestamp = timezone.now(),
        level = 'Error',
        status_code = '500',
        message = f'{str(e)} at Payment/paystack_webhook',
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