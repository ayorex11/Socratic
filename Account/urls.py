from django.urls import path
from . import views

urlpatterns = [
    path('get_all_users/', views.get_all_users),
    path('google/', views.google_auth),
    path('check-student-eligibility/', views.check_student_eligibility),
]