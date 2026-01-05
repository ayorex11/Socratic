from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import time
import uuid
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
import json
import requests
from django.conf import settings
import os
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
    if not user.is_premium_active and user.number_of_generations >= 3:
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



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def download_pdf(request, pk):
    user = request.user
    try:
        result = ProcessingResult.objects.get(pk=pk, user=user)
        
        if not result.pdf_report:
            return Response(
                {'error': 'PDF report not available',
                 'status': result.status},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the file URL
        file_url = result.pdf_report.url
        
        # Fetch the file from storage
        response = requests.get(file_url, stream=True)
        
        if response.status_code == 200:
            # Create filename
            filename = f"{result.document_title}_report.pdf".replace(' ', '_')
            
            # Create HTTP response with file
            file_response = HttpResponse(
                response.content,
                content_type='application/pdf'
            )
            file_response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            LogEntry.objects.create(
                user=user,
                timestamp=timezone.now(),
                level='Normal',
                status_code='200',
                message='PDF downloaded successfully'
            )
            
            return file_response
        else:
            return Response(
                {'error': 'Failed to retrieve file',
                 'status': result.status},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except ProcessingResult.DoesNotExist:
        return Response(
            {'error': 'Processing result not found',
             'status': result.status},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        LogEntry.objects.create(
            user=user,
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Unexpected error in download_pdf_file: {str(e)}'
        )
        return Response(
            {'error': 'Server error',
             'status': result.status},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def download_audio(request, pk):
    user = request.user
    try:
        result = ProcessingResult.objects.get(pk=pk, user=user)
        
        if not result.audio_summary:
            return Response(
                {'error': 'Audio summary not available',
                 'status': result.status},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the file URL
        file_url = result.audio_summary.url
        
        # Fetch the file from storage
        response = requests.get(file_url, stream=True)
        
        if response.status_code == 200:
            # Create filename
            filename = f"{result.document_title}_summary.mp3".replace(' ', '_')
            
            # Create HTTP response with file
            file_response = HttpResponse(
                response.content,
                content_type='audio/mpeg'
            )
            file_response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            LogEntry.objects.create(
                user=user,
                timestamp=timezone.now(),
                level='Normal',
                status_code='200',
                message='Audio downloaded successfully'
            )
            
            return file_response
        else:
            return Response(
                {'error': 'Failed to retrieve file',
                 'status': result.status},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except ProcessingResult.DoesNotExist:
        return Response(
            {'error': 'Processing result not found', 
            'status': result.status},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        LogEntry.objects.create(
            user=user,
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Unexpected error in download_audio_file: {str(e)}'
        )
        return Response(
            {'error': 'Server error',
             'status': result.status},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def processing_status_stream(request, pk):
    """
    SSE endpoint that streams processing status updates for a specific document.
    Authentication happens via standard Authorization header (handled by DRF).
    """
    user = request.user
    
    def event_stream():
        """Generator function that yields SSE-formatted data"""
        try:
            # Verify the document exists and belongs to user
            try:
                result = ProcessingResult.objects.get(pk=pk, user=user)
            except ProcessingResult.DoesNotExist:
                yield f"event: error\ndata: {json.dumps({'error': 'Document not found'})}\n\n"
                return
            
            last_status = None
            last_stage = None
            last_progress = None
            retry_count = 0
            max_retries = 180  # 3 minutes with 1-second intervals
            
            # Send initial state immediately
            initial_data = {
                'id': str(result.id),
                'status': result.status,
                'processing_stage': result.processing_stage,
                'stage_progress': result.stage_progress,
                'stage_message': result.stage_message,
                'stage_label': result.get_processing_stage_display(),
                'quiz_generated': result.quiz_generated,
                'pdf_generated': result.pdf_generated,
                'audio_generated': result.audio_generated,
                'is_processing': result.status == 'PROCESSING',
                'timestamp': timezone.now().isoformat()
            }
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            last_status = result.status
            last_stage = result.processing_stage
            last_progress = result.stage_progress
            
            # Keep connection alive and check for updates
            while retry_count < max_retries:
                try:
                    # Refresh data from database
                    result.refresh_from_db()
                    
                    # Check if status/stage changed
                    current_status = result.status
                    current_stage = result.processing_stage
                    current_progress = result.stage_progress
                    
                    status_changed = (
                        last_status != current_status or
                        last_stage != current_stage or
                        last_progress != current_progress
                    )
                    
                    if status_changed:
                        # Prepare data to send
                        data = {
                            'id': str(result.id),
                            'status': result.status,
                            'processing_stage': result.processing_stage,
                            'stage_progress': result.stage_progress,
                            'stage_message': result.stage_message,
                            'stage_label': result.get_processing_stage_display(),
                            'quiz_generated': result.quiz_generated,
                            'pdf_generated': result.pdf_generated,
                            'audio_generated': result.audio_generated,
                            'is_processing': result.status == 'PROCESSING',
                            'timestamp': timezone.now().isoformat()
                        }
                        
                        # Format as SSE
                        yield f"data: {json.dumps(data)}\n\n"
                        
                        # Update tracking variables
                        last_status = current_status
                        last_stage = current_stage
                        last_progress = current_progress
                        
                        # Reset retry count on successful update
                        retry_count = 0
                        
                        # If processing is complete or failed, close connection
                        if result.status in ['COMPLETED', 'FAILED']:
                            yield f"event: close\ndata: {json.dumps({'message': 'Processing finished', 'status': result.status})}\n\n"
                            return
                    else:
                        # Send keepalive comment every 15 seconds
                        if retry_count % 15 == 0:
                            yield f": keepalive\n\n"
                    
                    # Wait before checking again
                    time.sleep(1)
                    retry_count += 1
                    
                except Exception as db_error:
                    yield f"event: error\ndata: {json.dumps({'error': f'Database error: {str(db_error)}'})}\n\n"
                    return
            
            # Connection timeout
            yield f"event: timeout\ndata: {json.dumps({'message': 'Connection timeout - please refresh'})}\n\n"
                
        except Exception as e:
            error_data = {'error': f'Unexpected error: {str(e)}'}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    # Critical SSE headers
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    response['Connection'] = 'keep-alive'
    response['Content-Encoding'] = 'none'  # Prevent compression
    
    # CORS headers for SSE
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:5173', 'http://localhost:3000', 'https://socratic-frontend-ashy.vercel.app']:
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_processing_status_stream(request):
    """
    SSE endpoint that streams status updates for ALL user's documents.
    Useful for dashboard view where multiple documents might be processing.
    """
    user = request.user
    
    def event_stream():
        """Generator function that yields SSE-formatted data for all documents"""
        try:
            last_states = {}
            retry_count = 0
            max_retries = 180  # 3 minutes
            
            # Send initial state
            results = ProcessingResult.objects.filter(user=user)
            initial_updates = []
            
            for result in results:
                result_id = str(result.id)
                state = (result.status, result.processing_stage, result.stage_progress)
                last_states[result_id] = state
                
                initial_updates.append({
                    'id': result_id,
                    'status': result.status,
                    'processing_stage': result.processing_stage,
                    'stage_progress': result.stage_progress,
                    'stage_message': result.stage_message,
                    'stage_label': result.get_processing_stage_display(),
                    'quiz_generated': result.quiz_generated,
                    'pdf_generated': result.pdf_generated,
                    'audio_generated': result.audio_generated,
                    'document_title': result.document_title,
                    'created_at': result.created_at.isoformat(),
                })
            
            if initial_updates:
                initial_data = {
                    'updates': initial_updates,
                    'timestamp': timezone.now().isoformat()
                }
                yield f"data: {json.dumps(initial_data)}\n\n"
            
            while retry_count < max_retries:
                try:
                    # Get all user's processing results
                    results = ProcessingResult.objects.filter(user=user)
                    
                    # Check if any have processing documents
                    has_processing = results.filter(status__in=['PROCESSING', 'PENDING']).exists()
                    
                    updates = []
                    for result in results:
                        result_id = str(result.id)
                        current_state = (
                            result.status,
                            result.processing_stage,
                            result.stage_progress
                        )
                        
                        # Check if this document's state changed
                        if last_states.get(result_id) != current_state:
                            updates.append({
                                'id': result_id,
                                'status': result.status,
                                'processing_stage': result.processing_stage,
                                'stage_progress': result.stage_progress,
                                'stage_message': result.stage_message,
                                'stage_label': result.get_processing_stage_display(),
                                'quiz_generated': result.quiz_generated,
                                'pdf_generated': result.pdf_generated,
                                'audio_generated': result.audio_generated,
                                'document_title': result.document_title,
                                'created_at': result.created_at.isoformat(),
                            })
                            last_states[result_id] = current_state
                    
                    # Send updates if any
                    if updates:
                        data = {
                            'updates': updates,
                            'timestamp': timezone.now().isoformat()
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        retry_count = 0  # Reset on successful update
                    
                    # If no processing documents, send completion and close
                    if not has_processing:
                        yield f"event: complete\ndata: {json.dumps({'message': 'All processing complete'})}\n\n"
                        return
                    
                    # Send keepalive
                    if retry_count % 15 == 0:
                        yield f": keepalive\n\n"
                    
                    # Wait before checking again
                    time.sleep(1)
                    retry_count += 1
                    
                except Exception as db_error:
                    yield f"event: error\ndata: {json.dumps({'error': f'Database error: {str(db_error)}'})}\n\n"
                    return
            
            # Timeout
            yield f"event: timeout\ndata: {json.dumps({'message': 'Connection timeout'})}\n\n"
                
        except Exception as e:
            error_data = {'error': f'Unexpected error: {str(e)}'}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    # Critical SSE headers
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    response['Connection'] = 'keep-alive'
    response['Content-Encoding'] = 'none'
    
    # CORS headers for SSE
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:5173', 'http://localhost:3000', 'https://socratic-frontend-ashy.vercel.app']:
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
    
    return response