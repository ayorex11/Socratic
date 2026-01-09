from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

from resetpassword.views import PasswordResetRequestView, PasswordResetConfirmAPIView

schema_view = get_schema_view(
    openapi.Info(
      title="Socratic API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="adewalemaxwell11@gmail.com"),
      license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('auth/', include('dj_rest_auth.urls')), 
    path('registration/', include('dj_rest_auth.registration.urls')),  
    path(
    'auth/password/reset/confirm/<str:uidb64>/<str:token>/', 
    PasswordResetConfirmAPIView.as_view(), 
    name='password_reset_confirm'
    ),
    path('resetpassword/', include('resetpassword.urls')),
    path('Account/', include('Account.urls')),
    path('socratic/', include('Socratic.urls')),
    path('pricing/', include('Pricing.urls')),
    path('log-entries/', include('logs.urls')),
    path('payment/', include('payment.urls')),
    path('quiz/', include('Quiz.urls')),
    path('accounts/', include('allauth.urls')),
]

