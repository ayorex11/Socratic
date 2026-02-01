"""
Rate limiting throttle class for payment endpoints
"""
from rest_framework.throttling import UserRateThrottle


class PaymentInitThrottle(UserRateThrottle):
    """
    Throttle class to limit payment initialization requests
    Prevents spam and potential DoS attacks
    """
    rate = '5/minute'  # Maximum 5 payment initializations per minute per user
