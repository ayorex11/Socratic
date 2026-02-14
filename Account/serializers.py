from rest_framework import serializers
from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import User
from django.db import IntegrityError

def email_address_exists(email):
    return User.objects.filter(email=email).exists()


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED)
    username = serializers.CharField(required=True, write_only=True)
    password1 = serializers.CharField(required=True, write_only=True)
    password2 = serializers.CharField(required=True, write_only=True)

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    ("A user is already registered with this e-mail address."))
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(
                ("The two password fields didn't match."))

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError(
                {"email": "A user is already registered with this email address."})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError(
                {"username": "A user is already registered with this username."})
        
        # --- Fingerprint Validation ---
        # We access the request context to check headers
        request = self.context.get('request')
        if request:
            fingerprint = request.headers.get('x-device-fingerprint')
            if fingerprint:
                from .utils import check_fingerprint_limit
                if not check_fingerprint_limit(fingerprint):
                    raise serializers.ValidationError(
                        {"non_field_errors": ["Maximum account limit reached for this device."]}
                    )
        
        return data

    def get_cleaned_data(self):
        return {
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'username': self.validated_data.get('username', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
        }
    
    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        setup_user_email(request, user, [])

        
        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')

        user.first_name = first_name
        user.last_name = last_name

        
        try:
            user.save()
            
            # --- Save Fingerprint ---
            from .utils import record_user_fingerprint
            record_user_fingerprint(user, request)
                
        except IntegrityError as e:
            raise serializers.ValidationError({"error": "A user with that username or email already exists."})
        
        return user

class UserDetailsSerializer(UserDetailsSerializer):
    
    class Meta:
        fields = ['email', 'username', 'first_name', 'last_name', 'premium_user', 'user_type', 'subscription_end_date', 'number_of_generations']
        read_only_fields = ['email', 'premium_user', 'user_type', 'subscription_end_date', 'username', 'number_of_generations']
        model = User

        
class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'date_joined','first_name', 'last_name', 'premium_user', 'user_type', 'subscription_end_date', 'username']
