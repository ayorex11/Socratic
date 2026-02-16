from dj_rest_auth.views import LoginView
from rest_framework.response import Response
from rest_framework import status
from .utils import check_fingerprint_limit, record_user_fingerprint

class CustomLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        # --- Fingerprint Check ---
        fingerprint = request.headers.get('x-device-fingerprint')
        
        # We enforce strict checking: if no fingerprint, we might want to block or allow.
        # For now, if provided, we check logic.
        if fingerprint:
             if not check_fingerprint_limit(fingerprint):
                 return Response(
                     {'non_field_errors': ['Maximum account limit reached for this device.']},
                     status=status.HTTP_400_BAD_REQUEST
                 )
        
        # Proceed with standard login
        response = super().post(request, *args, **kwargs)
        
        # If login successful, record the fingerprint
        if response.status_code == status.HTTP_200_OK and fingerprint:
            # self.user is set by dj_rest_auth after successful login
            if self.user:
                record_user_fingerprint(self.user, request)
                
        return response
