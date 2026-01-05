from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

User = get_user_model()

class SSEAuthMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate SSE connections via query parameter token.
    SSE cannot send custom headers, so we use query params for auth.
    """
    
    def process_request(self, request):
        # Only process SSE endpoints
        if 'stream' not in request.path:
            return None
            
        # Get token from query parameter
        token = request.GET.get('token')
        
        if token:
            try:
                # Validate the JWT token
                UntypedToken(token)
                
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
                
            except (InvalidToken, TokenError) as e:
                pass
        
        return None