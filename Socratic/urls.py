from django.urls import path
from . import views
urlpatterns = [
    path('create_processing/',views.create_processing),
    path('list_processing_results/', views.list_processing_results),
    path('retrieve/<uuid:pk>/', views.get_processing_result),
    path('download_audio/<uuid:pk>/', views.download_audio),
    path('download_pdf/<uuid:pk>/', views.download_pdf),
    path('delete/<uuid:pk>/', views.delete_processing_result),
    path('processing-status-stream/<uuid:pk>/', views.processing_status_stream),
    path('all-processing-status-stream/', views.all_processing_status_stream),
    path('get_all_documents/', views.get_all_documents),
]