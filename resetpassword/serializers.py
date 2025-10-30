from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import custom_token_generator 

UserModel = get_user_model()

# --- Password Reset Request (Email Sending) ---
class CustomPasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Remove PasswordResetForm - do manual validation
        if not UserModel.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("Invalid email address."))
        return value

    def save(self):
        # MANUAL IMPLEMENTATION - No PasswordResetForm
        email = self.validated_data['email']
        user = UserModel.objects.get(email=email)
        
        # Generate token and UID manually
        token = custom_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create the EXACT URL you want
        reset_url = f"http://localhost:5173/reset-password/confirm/{uid}/{token}/"
        
        # Create the EXACT email content you want
        subject = "Password Reset Request"
        message = f"""Hello from our app!

        You're receiving this email because you requested a password reset for your user account.
        It can be safely ignored if you did not request a password reset. Click the link below to reset your password.

        {reset_url}

        In case you forgot, your username is {user.get_username()}.

        Thank you for using our app!"""
        
        # Send email manually
        send_mail(
            subject,
            message,
            'noreply@socratic.com',  # From email
            [user.email],  # To email
            fail_silently=False,
        )

# --- Password Reset Confirmation (Keep this as is) ---
class CustomPasswordResetConfirmSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(max_length=128, min_length=8)
    new_password2 = serializers.CharField(max_length=128, min_length=8)
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password1'] != attrs['new_password2']:
            raise ValidationError({'new_password2': [_("The two password fields didn't match.")]})

        # Decode UID and retrieve user
        try:
            uid = urlsafe_base64_decode(attrs['uid']).decode()
            self.user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            raise ValidationError({'uid': [_('Invalid value')]})

        # Check Token using the CUSTOM generator
        if not custom_token_generator.check_token(self.user, attrs['token']):
            raise ValidationError({'token': [_('Invalid value')]})
            
        return attrs

    def save(self):
        self.user.set_password(self.validated_data['new_password1'])
        self.user.save()