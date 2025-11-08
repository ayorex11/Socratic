from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class SubscriptionCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            user = request.user
            
            # Check if premium subscription has expired
            if user.premium_user and user.subscription_end_date:
                if user.subscription_end_date < timezone.now().date():
                    user.premium_user = False
                    user.subscription_end_date = None
                    user.save(update_fields=['premium_user', 'subscription_end_date'])
        
        return None