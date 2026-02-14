from .models import UserFingerprint

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
