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
