from rest_framework import generics, response, status
from rest_framework.permissions import AllowAny
from .serializers import CustomPasswordResetRequestSerializer, CustomPasswordResetConfirmSerializer

# --- Password Reset Request View ---
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = CustomPasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save() 
        return response.Response(
            {'detail': 'Password reset e-mail has been sent.'},
            status=status.HTTP_200_OK
        )

# --- Password Reset Confirmation View ---
class PasswordResetConfirmAPIView(generics.GenericAPIView):
    serializer_class = CustomPasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(
            {'detail': 'Password has been successfully reset.'},
            status=status.HTTP_200_OK
        )