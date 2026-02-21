from .models import UserFingerprint
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def check_fingerprint_limit(fingerprint):
    """
    Checks if the given fingerprint has exceeded the account limit.
    Returns True if allowed, False if blocked.
    Limit: Max 2 accounts per device.
    """
    if not fingerprint:
        return True
        
    existing_count = UserFingerprint.objects.filter(device_fingerprint=fingerprint).values('user').distinct().count()
    return existing_count < 2

def record_user_fingerprint(user, request):
    """
    Records the device fingerprint for a user.
    """
    fingerprint = request.headers.get('x-device-fingerprint')
    if fingerprint:
        UserFingerprint.objects.get_or_create(
            user=user,
            device_fingerprint=fingerprint,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
        )

def get_email_domain(email):
    """
    Extracts the domain from an email address.
    """
    if not email or '@' not in email:
        return ''
    return email.lower().split('@')[-1]

def is_student_email(email):
    """
    Checks if an email belongs to a student/educational institution.
    """
    domain = get_email_domain(email)
    if not domain:
        return False
        
    # Keywords that indicate educational institutions
    student_keywords = ['university', 'college', 'school', 'edu', 'ac', 'student']
    
    # Check if domain contains any student keywords
    return any(keyword in domain for keyword in student_keywords)


def is_new_fingerprint_for_user(user, fingerprint):
    """
    Checks if this fingerprint is new for the given user.
    Returns True if new (never seen before), False if already recorded.
    """
    if not fingerprint:
        return False
    return not UserFingerprint.objects.filter(
        user=user,
        device_fingerprint=fingerprint
    ).exists()


def send_new_device_alert_email(user, request):
    """
    Sends an alert email to the user when their account is accessed
    from a new/unrecognized device or location.
    """
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'Unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    login_time = timezone.now().strftime('%B %d, %Y at %I:%M %p UTC')

    subject = '[SocraSeek] New Device Login Detected'

    message = f"""Hi {user.get_full_name() or user.username},

We detected a login to your SocraSeek account from a new device or location.

Login Details:
• Time: {login_time}
• IP Address: {ip_address}
• Device: {user_agent}

If this was you, no action is needed.

If this was NOT you, we strongly recommend you:
1. Change your password immediately at {settings.FRONTEND_URL}/profile
2. Use the "Logout All Devices" option on your profile page to end all other sessions.

Stay safe,
The SocraSeek Team

---
This is an automated security alert. Please do not reply to this email.
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        # Don't block login if email fails
        pass

