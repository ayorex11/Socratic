from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class SubscriptionCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            user = request.user
            
            # Check if premium/student subscription has expired
            if user.user_type in ['premium', 'student'] and user.subscription_end_date:
                if user.subscription_end_date < timezone.now().date():
                    user.premium_user = False
                    user.user_type = 'free'
                    user.subscription_end_date = None
                    user.save(update_fields=['premium_user', 'user_type', 'subscription_end_date'])
        
        return None