from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        now = timezone.now()
        user = self.model(
            username=username,
            email=email,
            date_joined=now,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Is Admin must have is_admin=True.')

        return self.create_user(username, email, password, **extra_fields)




class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('student', 'Student'),
    ]
    
    first_name = models.CharField(max_length=250, blank=True)
    last_name = models.CharField(max_length=250, blank=True)
    email = models.EmailField('email address', unique=True)
    username = models.CharField(max_length=50, unique=True)
    premium_user = models.BooleanField(default=False)  # Kept for backward compatibility
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='free')
    subscription_end_date = models.DateField(blank=True, null=True)
    number_of_generations = models.IntegerField(default=0)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, null=True)
    is_admin = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email',]

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email

    def __str__(self):
        return self.username
    
    @property
    def is_premium_active(self):
        """Check if user has active premium or student subscription"""
        # Check if user has premium or student tier
        if self.user_type not in ['premium', 'student']:
            return False
        
        if self.subscription_end_date:
            if self.subscription_end_date < timezone.now().date():
                # Subscription expired - downgrade to free
                self.premium_user = False
                self.user_type = 'free'
                self.subscription_end_date = None
                self.save(update_fields=['premium_user', 'user_type', 'subscription_end_date'])
                return False
        
        return True
    
    def is_student_email(self):
        """Check if user's email is from a student/educational institution"""
        if not self.email:
            return False
        
        email_lower = self.email.lower()
        domain = email_lower.split('@')[-1] if '@' in email_lower else ''
        
        # Keywords that indicate educational institutions
        student_keywords = ['university', 'college', 'school', 'edu', 'ac', 'student']
        
        # Check if domain contains any student keywords
        return any(keyword in domain for keyword in student_keywords)


class UserFingerprint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fingerprints')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=255, db_index=True)
    browser_fingerprint = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.device_fingerprint[:8]}..."
