from resetpassword.views import PasswordResetRequestView, PasswordResetConfirmAPIView
from django.urls import path
urlpatterns = [
    path('password/reset/', PasswordResetRequestView.as_view(), name='custom_password_reset'),
    path('password/reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='custom_password_reset_confirm'),

]