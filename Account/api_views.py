from dj_rest_auth.views import LoginView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from .utils import record_user_fingerprint, is_new_fingerprint_for_user, send_new_device_alert_email

class CustomLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        fingerprint = request.headers.get('x-device-fingerprint')
        
        # Proceed with standard login (no fingerprint blocking)
        response = super().post(request, *args, **kwargs)
        
        # If login successful, check if new device and send alert
        if response.status_code == status.HTTP_200_OK and fingerprint:
            if self.user:
                if is_new_fingerprint_for_user(self.user, fingerprint):
                    send_new_device_alert_email(self.user, request)
                record_user_fingerprint(self.user, request)
                
        return response


class LogoutAllDevicesView(APIView):
    """
    Blacklists all outstanding refresh tokens for the authenticated user,
    effectively logging them out of every device.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

            tokens = OutstandingToken.objects.filter(user=request.user)
            blacklisted_count = 0
            for token in tokens:
                _, created = BlacklistedToken.objects.get_or_create(token=token)
                if created:
                    blacklisted_count += 1

            response = Response(
                {'message': f'Successfully logged out of all devices. {blacklisted_count} session(s) terminated.'},
                status=status.HTTP_200_OK
            )
            response.delete_cookie('my-app-auth', path='/', samesite='None')
            response.delete_cookie('my-refresh-token', path='/', samesite='None')
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to logout all devices: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomResendEmailVerificationView(APIView):
    """
    Resends a verification email only if the email exists in the system.
    Returns 404 if the email is not found.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from allauth.account.models import EmailAddress

        email = request.data.get('email')
        if not email:
            return Response(
                {'detail': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        email_address = EmailAddress.objects.filter(email=email).first()

        if not email_address:
            return Response(
                {'detail': 'Account not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if email_address.verified:
            return Response(
                {'detail': 'This email is already verified.'},
                status=status.HTTP_200_OK
            )

        email_address.send_confirmation(request)
        return Response(
            {'detail': 'Verification email sent successfully.'},
            status=status.HTTP_200_OK
        )

