from django.urls import path
from . import views
from .api_views import LogoutAllDevicesView

urlpatterns = [
    path('get_all_users/', views.get_all_users),
    path('google/', views.google_auth),
    path('check-student-eligibility/', views.check_student_eligibility),
    path('logout-all-devices/', LogoutAllDevicesView.as_view()),
]