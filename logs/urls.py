from django.urls import path
from . import views

urlpatterns = [
    path('list_log_entries/', views.list_log_entries),
    path('get_log_entry/<int:pk>/', views.get_log_entry),
    path('filter_log_entry_by_status_code/<str:status>/', views.filter_log_entry_by_status_code),
    path('filter_by_time_range/', views.filter_by_time_range),
]