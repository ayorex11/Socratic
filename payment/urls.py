from . import views
from django.urls import path

urlpatterns = [
    path('initialize_deposit/', views.initialize_deposit),
    path('paystack-webhook/', views.paystack_webhook),
    path('transaction_history/', views.transaction_history),
]