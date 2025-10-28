from rest_framework.throttling import UserRateThrottle

class UserBurstRateThrottle(UserRateThrottle):
    scope = 'user_burst'

class UserSustainedRateThrottle(UserRateThrottle):
    scope = 'user_sustained'
