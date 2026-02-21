from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from .models import User 
from rest_framework import status
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests
import os

@api_view(['GET'])
@permission_classes([IsAuthenticated])

def get_all_users(request):
	user = request.user
	xyz = User.objects.all()
	if user.is_admin == False:
		return Response({'message':'unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

	serializer = UserSerializer(xyz, many=True)
	data = {'message': 'success',
			'data': serializer.data}

	return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Handle Google OAuth authentication
    Creates new user if doesn't exist, logs in if exists
    """
    try:
        # Get the credential (ID token) from the request
        credential = request.data.get('credential')
        access_token = request.data.get('access_token')
        
        # Use whichever token was provided
        token = credential or access_token
        
        if not token:
            return Response(
                {'error': 'Google token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the token with Google
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                os.getenv('GOOGLE_OAUTH_CLIENT_ID')
            )
            
            # Check if the token is for the correct client ID
            if idinfo['aud'] != os.getenv('GOOGLE_OAUTH_CLIENT_ID'):
                return Response(
                    {'error': 'Invalid token audience'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except ValueError as e:
            return Response(
                {'error': f'Invalid Google token: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Token verification failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract user info
        email = idinfo.get('email')
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')
        google_id = idinfo.get('sub')
        
        if not email:
            return Response(
                {'error': 'Email not provided by Google'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists by email
        try:
            user = User.objects.get(email=email)
            created = False
        except User.DoesNotExist:
            # --- Fingerprint limit check for NEW registrations only ---
            fingerprint = request.headers.get('x-device-fingerprint')
            if fingerprint:
                from .utils import check_fingerprint_limit
                if not check_fingerprint_limit(fingerprint):
                     return Response(
                         {'non_field_errors': ['Maximum account limit reached for this device.']},
                         status=status.HTTP_400_BAD_REQUEST
                     )

            # Create new user
            base_username = email.split('@')[0]
            username = base_username
            
            # Handle username collisions
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,  # Auto-activate Google users
            )
            created = True

        # Generate JWT tokens with expiration info
        refresh = RefreshToken.for_user(user)
        access_token_obj = refresh.access_token
        
        # --- Record Fingerprint & Send Alert for Existing Users ---
        fingerprint = request.headers.get('x-device-fingerprint')
        if fingerprint:
            from .utils import record_user_fingerprint, is_new_fingerprint_for_user, send_new_device_alert_email
            if not created and is_new_fingerprint_for_user(user, fingerprint):
                send_new_device_alert_email(user, request)
            record_user_fingerprint(user, request)
        
        return Response({
            'access': str(access_token_obj),
            'refresh': str(refresh),
            'access_expiration': access_token_obj['exp'],
            'refresh_expiration': refresh['exp'],
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'premium_user': user.premium_user,
            },
            'is_new_user': created
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Authentication failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_student_eligibility(request):
    from .utils import is_student_email, get_email_domain
    
    email = request.user.email
    
    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    eligible = is_student_email(email)
    domain = get_email_domain(email)
    
    if eligible:
        return Response({
            'eligible': True,
            'email': email,
            'domain': domain,
            'message': 'Email is eligible for student plan'
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'eligible': False,
            'email': email,
            'domain': domain,
            'message': 'Email is not eligible for student plan. Please use a university, college, or school email address.'
        }, status=status.HTTP_200_OK)
