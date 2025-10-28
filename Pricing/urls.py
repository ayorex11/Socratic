from django.urls import path
from . import views

urlpatterns = [
    path('list_pricing/', views.list_pricing),
    path('get_pricing/<int:pk>/', views.get_pricing),
    path('create_pricing/', views.create_pricing),
    path('modify_pricing/<int:pk>/', views.modify_pricing),
    path('delete_pricing/<int:pk>/', views.delete_pricing),
]

