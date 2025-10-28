from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import time
import uuid

from .models import ProcessingResult
from .serializers import DocumentProcessingSerializer, ProcessingResultSerializer, MinimalProcessingResultSerializer
from .utils.document_processor import DocumentProcessor
from .utils.ai_processor import PremiumAIProcessor
from .utils.free_ai_processor import AIProcessor
from .utils.text_to_speech import TextToSpeech
from .utils.pdf_generator import PDFGenerator, AdvancedPDFGenerator
from .utils.quiz_generator import AdvancedQuizGenerator, AIPoweredQuizGenerator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view, permission_classes, parser_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from .utils.throttle import UserBurstRateThrottle, UserSustainedRateThrottle
from logs.models import LogEntry   
from datetime import datetime
from .tasks import process_document_task
from django.utils import timezone
from .utils.file_helpers import _save_temp_file, _cleanup_temp_file


@swagger_auto_schema(methods=['POST'], request_body=DocumentProcessingSerializer)
@api_view(['POST'])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def create_processing(request):
    """
    Handles file upload, saves files temporarily, creates a PENDING database record, 
    dispatches the long-running task to Celery, and returns 202 ACCEPTED immediately.
    """
    user = request.user
    study_temp_path = None
    past_questions_temp_path = None

    # --- 1. Generation Limit Check ---
    if not user.premium_user and user.number_of_generations >= 3:
        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Normal', status_code='403',
            message='generation limit hit at create_processing'
        )
        return Response(
            {'error': 'Free users can only process 3 documents. Please upgrade to premium for unlimited access.'},
            status=status.HTTP_403_FORBIDDEN
        )
        
    # --- 2. Input Validation ---
    serializer = DocumentProcessingSerializer(data=request.data)
    if not serializer.is_valid():
        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Error', status_code='400',
            message='invalid input at create_processing'
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    data = serializer.validated_data
    
    try:
        study_material = data['study_material']
        past_questions = data.get('past_questions')
        document_title = data['document_title']
        
        # --- 3. Save files synchronously and get paths ---
        study_temp_path = _save_temp_file(study_material)
        past_questions_temp_path = _save_temp_file(past_questions) if past_questions else None
        
        # --- 4. Create INITIAL PENDING database record ---
        result = ProcessingResult.objects.create(
            user=user,
            document_title=document_title,
            original_filename=study_material.name,
            used_past_questions=bool(past_questions),
            status='PENDING', 
        )
        
        # --- 5. Dispatch task to Celery ---
        process_document_task.delay(
            result.id, 
            user.id, 
            study_temp_path, 
            past_questions_temp_path, 
            study_material.name,
            document_title
        )
        
        # --- 6. Update user count immediately ---
        # Note: This is an architectural choice. Could also be done inside the task on success.
        user.number_of_generations += 1
        user.save()
        
        # --- 7. Log and Return Success ---
        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Normal', status_code='202',
            message=f'Processing initiated (Task ID: {result.id})'
        )
        
        result_serializer = MinimalProcessingResultSerializer(result)
        return Response(result_serializer.data, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        # --- 8. Handle synchronous failure (e.g., file system error, DB error on creation) ---
        _cleanup_temp_file(study_temp_path)
        if past_questions_temp_path:
            _cleanup_temp_file(past_questions_temp_path)

        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Error', status_code='500',
            message=f'Failed to initiate processing: {str(e)}'
        )
        return Response(
            {'error': f'Failed to upload files or start processing: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@permission_classes([IsAuthenticated])
@api_view(['GET'])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def list_processing_results(request):
    """Get all processing results"""
    user = request.user
    results = ProcessingResult.objects.filter(user=user)
    serializer = MinimalProcessingResultSerializer(results, many=True)
    LogEntry.objects.create(
        timestamp = datetime.now(),
        level = 'Normal',
        status_code = '200',
        message = 'successful query at Socratic/list_processing_results',
        user = user
    )
    return Response(serializer.data)

@permission_classes([IsAuthenticated])
@api_view(['GET'])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def get_processing_result(request, pk):
    """Get specific processing result"""
    user = request.user
    try:
        result = ProcessingResult.objects.get(pk=pk, user=user)
        serializer = ProcessingResultSerializer(result)
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Normal',
            status_code = '200',
            message = 'successful query at Socratic/get_processing_result',
            user = user
        )
        return Response(serializer.data)
    except ProcessingResult.DoesNotExist:
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Error',
            status_code = '404',
            message = 'processing result not found at Socratic/get_processing_result',
            user = user
        )
        return Response(
            {'error': 'Processing result not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@permission_classes([IsAuthenticated])
@api_view(['GET'])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def download_pdf(request, pk):
    """Force download of PDF report"""
    user = request.user
    try:
        result = ProcessingResult.objects.get(pk=pk, user=user)
        if not result.pdf_report:
            LogEntry.objects.create(
                timestamp = datetime.now(),
                level = 'Error',
                status_code = '404',
                message = 'pdf report not found at Socratic/download_pdf',
                user = user
            )
            return Response(
                {'error': 'PDF report not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Normal',
            status_code = '200',
            message = 'successful pdf download at Socratic/download_pdf',
            user = user
        )
        return Response({
            'pdf_url': result.pdf_report.url,
            'filename': f"{result.document_title}_report.pdf"
        })
    
    except ProcessingResult.DoesNotExist:
        LogEntry.objects.create(
        timestamp = datetime.now(),
        level = 'Error',   
        status_code = '404',
        message = 'processing result not found at Socratic/download_pdf',
        user = user
        )  
        return Response(
            {'error': 'Processing result not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@permission_classes([IsAuthenticated])
@api_view(['GET'])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def download_audio(request, pk):
    """Force download of audio summary"""
    user = request.user
    try:
        result = ProcessingResult.objects.get(pk=pk, user=user)
        if not result.audio_summary:
            LogEntry.objects.create(
                timestamp = datetime.now(),
                level = 'Error',
                status_code = '404',
                message = 'audio summary not found at Socratic/download_audio',
                user = user
            )
            return Response(
                {'error': 'Audio summary not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Normal',
            status_code = '200',
            message = 'successful audio download at Socratic/download_audio',
            user = user
        )
        return Response({
            'audio_url': result.audio_summary.url,
            'filename': f"{result.document_title}_summary.mp3"
        })
        
    except ProcessingResult.DoesNotExist:
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Error',
            status_code = '404',
            message = 'processing result not found at Socratic/download_audio',
            user = user
        )
        return Response(
            {'error': 'Processing result not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_processing_result(request, pk):
    """Delete a specific processing result and its associated files"""
    user = request.user
    try:
        result = ProcessingResult.objects.get(id=pk, user=user)
        result.delete()
        user.number_of_generations = max(0, user.number_of_generations - 1)
        user.save()
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Normal',
            status_code = '204',
            message = 'successful deletion at Socratic/delete_processing_result',
            user = user
        )
        return Response({'message': 'Processing result deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    except ProcessingResult.DoesNotExist:
        LogEntry.objects.create(
            timestamp = datetime.now(),
            level = 'Error',
            status_code = '404',
            message = 'processing result not found at Socratic/delete_processing_result',
            user = user
        )
        return Response(
            {'error': 'Processing result not found'},
            status=status.HTTP_404_NOT_FOUND
        )