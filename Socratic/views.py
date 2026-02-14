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
from .utils.file_helpers import _save_uploaded_file_to_storage, _cleanup_uploaded_file
from Account.models import User as CustomUser
from Quiz.models import Quiz
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
    study_file_path = None
    past_questions_file_path = None

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
        
        # --- 3. Save files to R2 storage (accessible to all containers) ---
        study_file_path = _save_uploaded_file_to_storage(study_material)
        past_questions_file_path = _save_uploaded_file_to_storage(past_questions) if past_questions else None
        
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
            study_file_path,  # R2 storage path
            past_questions_file_path,  # R2 storage path or None
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
        _cleanup_uploaded_file(study_file_path)
        if past_questions_file_path:
            _cleanup_uploaded_file(past_questions_file_path)

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
    results = ProcessingResult.objects.filter(user=user, is_deleted=False)
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
        # First try to get the document (any document, not just user's)
        result = ProcessingResult.objects.get(pk=pk)
        
        # Check access permissions
        # Users can access their own documents OR community documents based on premium status
        if result.user != user:
            # This is someone else's document - check if user has access
            if not user.premium_user and result.user.premium_user:
                return Response(
                    {'error': 'Premium subscription required to access this document'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
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
                message=f'PDF downloaded successfully (document: {pk})'
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
            {'error': 'Processing result not found'},
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
            {'error': 'Server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle, UserBurstRateThrottle, UserSustainedRateThrottle])
def download_audio(request, pk):
    user = request.user
    try:
        # First try to get the document (any document, not just user's)
        result = ProcessingResult.objects.get(pk=pk)
        
        # Check access permissions
        # Users can access their own documents OR community documents based on premium status
        if result.user != user:
            # This is someone else's document - check if user has access
            if not user.premium_user and result.user.premium_user:
                return Response(
                    {'error': 'Premium subscription required to access this document'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
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
                message=f'Audio downloaded successfully (document: {pk})'
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
            {'error': 'Processing result not found'}, 
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
            {'error': 'Server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_processing_result(request, pk):
    """Delete a specific processing result and its associated files"""
    user = request.user
    try:
        result = ProcessingResult.objects.get(id=pk, user=user)
        result.is_deleted = True
        result.deleted_at = datetime.now()
        result.save()
        # user.number_of_generations = max(0, user.number_of_generations - 1)  <-- REMOVED: Count is now lifetime
        # user.save()
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
    

from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.authentication import JWTAuthentication

import asyncio
from asgiref.sync import sync_to_async

@require_http_methods(["GET"])
async def processing_status_stream(request, pk):
    """SSE endpoint for single document"""
    # Manual JWT authentication - Wrap sync auth in sync_to_async
    try:
        @sync_to_async
        def authenticate_user():
            auth = JWTAuthentication()
            try:
                user_auth = auth.authenticate(request)
            except Exception:
                return None
            return user_auth
            
        user_auth = await authenticate_user()
        
        if user_auth is None:
            return HttpResponse(
                json.dumps({'error': 'Authentication required'}),
                status=401,
                content_type='application/json'
            )
        user = user_auth[0]
    except Exception as e:
        return HttpResponse(
            json.dumps({'error': 'Invalid token'}),
            status=401,
            content_type='application/json'
        )
    
    async def event_stream():
        try:
            # Sync wrapper for initial DB fetch
            get_result = sync_to_async(ProcessingResult.objects.get)
            
            try:
                result = await get_result(pk=pk, user=user)
            except ProcessingResult.DoesNotExist:
                yield f"event: error\ndata: {json.dumps({'error': 'Document not found'})}\n\n"
                return
            
            last_status = None
            last_stage = None
            last_progress = None
            retry_count = 0
            max_retries = 300 # 5 minutes timeout
            
            # Helper to get data safely
            @sync_to_async
            def get_initial_data(res):
                return {
                    'id': str(res.id),
                    'status': res.status,
                    'processing_stage': res.processing_stage,
                    'stage_progress': res.stage_progress,
                    'stage_message': res.stage_message,
                    'stage_label': res.get_processing_stage_display(),
                    'quiz_generated': res.quiz_generated,
                    'pdf_generated': res.pdf_generated,
                    'audio_generated': res.audio_generated,
                    'is_processing': res.status == 'PROCESSING',
                    'timestamp': timezone.now().isoformat()
                }

            initial_data = await get_initial_data(result)
            yield f"data: {json.dumps(initial_data)}\n\n"
            yield "retry: 3000\n\n" # Tell client to reconnect in 3s if connection drops
            
            last_status = initial_data['status']
            last_stage = initial_data['processing_stage']
            last_progress = initial_data['stage_progress']
            
            # Helper to refresh and get data
            @sync_to_async
            def check_updates(res_id, u):
                r = ProcessingResult.objects.get(pk=res_id, user=u)
                return {
                    'id': str(r.id),
                    'status': r.status,
                    'processing_stage': r.processing_stage,
                    'stage_progress': r.stage_progress,
                    'stage_message': r.stage_message,
                    'stage_label': r.get_processing_stage_display(),
                    'quiz_generated': r.quiz_generated,
                    'pdf_generated': r.pdf_generated,
                    'audio_generated': r.audio_generated,
                    'is_processing': r.status == 'PROCESSING',
                    'timestamp': timezone.now().isoformat()
                }

            while retry_count < max_retries:
                try:
                    current_data = await check_updates(pk, user)
                    
                    current_status = current_data['status']
                    current_stage = current_data['processing_stage']
                    current_progress = current_data['stage_progress']
                    
                    status_changed = (
                        last_status != current_status or
                        last_stage != current_stage or
                        last_progress != current_progress
                    )
                    
                    if status_changed:
                        yield f"data: {json.dumps(current_data)}\n\n"
                        
                        last_status = current_status
                        last_stage = current_stage
                        last_progress = current_progress
                        
                        retry_count = 0
                        
                        if current_status in ['COMPLETED', 'FAILED']:
                            yield f"event: close\ndata: {json.dumps({'message': 'Processing finished', 'status': current_status})}\n\n"
                            return
                    else:
                        # Send keepalive every 10 seconds (approx 10 loops)
                        if retry_count % 10 == 0:
                            yield f": keepalive\n\n"
                    
                    await asyncio.sleep(1)
                    retry_count += 1
                    
                except Exception as db_error:
                    yield f"event: error\ndata: {json.dumps({'error': f'Database error: {str(db_error)}'})}\n\n"
                    await asyncio.sleep(2) # Backoff briefly on error
                    
            yield f"event: timeout\ndata: {json.dumps({'message': 'Connection timeout - please refresh'})}\n\n"
                
        except Exception as e:
            error_data = {'error': f'Unexpected error: {str(e)}'}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    response['Content-Encoding'] = 'none'
    
    return response


@require_http_methods(["GET"])
async def all_processing_status_stream(request):
    """SSE endpoint for all documents"""
    # Manual JWT authentication
    try:
        @sync_to_async
        def authenticate_user():
            auth = JWTAuthentication()
            try:
                user_auth = auth.authenticate(request)
            except Exception:
                return None
            return user_auth
            
        user_auth = await authenticate_user()
        
        if user_auth is None:
            return HttpResponse(
                json.dumps({'error': 'Authentication required'}),
                status=401,
                content_type='application/json'
            )
        user = user_auth[0]
    except Exception as e:
        return HttpResponse(
            json.dumps({'error': 'Invalid token'}),
            status=401,
            content_type='application/json'
        )
    
    async def event_stream():
        try:
            last_states = {}
            retry_count = 0
            max_retries = 180
            
            # Helper to fetch initial state
            @sync_to_async
            def get_all_results_data(u):
                res_queryset = ProcessingResult.objects.filter(user=u)
                data_list = []
                states = {}
                for res in res_queryset:
                    res_id = str(res.id)
                    states[res_id] = (res.status, res.processing_stage, res.stage_progress)
                    data_list.append({
                        'id': res_id,
                        'status': res.status,
                        'processing_stage': res.processing_stage,
                        'stage_progress': res.stage_progress,
                        'stage_message': res.stage_message,
                        'stage_label': res.get_processing_stage_display(),
                        'quiz_generated': res.quiz_generated,
                        'pdf_generated': res.pdf_generated,
                        'audio_generated': res.audio_generated,
                        'document_title': res.document_title,
                        'created_at': res.created_at.isoformat(),
                    })
                return data_list, states

            initial_updates, last_states = await get_all_results_data(user)
            
            if initial_updates:
                initial_data = {
                    'updates': initial_updates,
                    'timestamp': timezone.now().isoformat()
                }
                yield f"data: {json.dumps(initial_data)}\n\n"
            yield "retry: 3000\n\n" # Tell client to reconnect in 3s if connection drops
            
            # Helper to check for changes
            @sync_to_async
            def check_all_updates(u, current_last_states):
                res_queryset = ProcessingResult.objects.filter(user=u)
                has_active = res_queryset.filter(status__in=['PROCESSING', 'PENDING']).exists()
                
                new_updates = []
                updated_states = current_last_states.copy()
                
                for res in res_queryset:
                    res_id = str(res.id)
                    current_state = (res.status, res.processing_stage, res.stage_progress)
                    
                    if current_last_states.get(res_id) != current_state:
                        new_updates.append({
                            'id': res_id,
                            'status': res.status,
                            'processing_stage': res.processing_stage,
                            'stage_progress': res.stage_progress,
                            'stage_message': res.stage_message,
                            'stage_label': res.get_processing_stage_display(),
                            'quiz_generated': res.quiz_generated,
                            'pdf_generated': res.pdf_generated,
                            'audio_generated': res.audio_generated,
                            'document_title': res.document_title,
                            'created_at': res.created_at.isoformat(),
                        })
                        updated_states[res_id] = current_state
                
                return new_updates, updated_states, has_active

            while retry_count < max_retries:
                try:
                    updates, new_states, has_processing = await check_all_updates(user, last_states)
                    last_states = new_states
                    
                    if updates:
                        data = {
                            'updates': updates,
                            'timestamp': timezone.now().isoformat()
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        retry_count = 0
                    
                    if not has_processing:
                        yield f"event: complete\ndata: {json.dumps({'message': 'All processing complete'})}\n\n"
                        return
                    
                    if retry_count % 10 == 0:
                        yield f": keepalive\n\n"
                    
                    await asyncio.sleep(1)
                    retry_count += 1
                    
                except Exception as db_error:
                    yield f"event: error\ndata: {json.dumps({'error': f'Database error: {str(db_error)}'})}\n\n"
                    await asyncio.sleep(2)
            
            yield f"event: timeout\ndata: {json.dumps({'message': 'Connection timeout'})}\n\n"
                
        except Exception as e:
            error_data = {'error': f'Unexpected error: {str(e)}'}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    response['Content-Encoding'] = 'none'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_documents(request):
    user = request.user
    
    # Premium users see all community docs, free users only see free community docs
    if user.premium_user:
        results = ProcessingResult.objects.exclude(user=user).filter(status='COMPLETED')
    else:
        results = ProcessingResult.objects.filter(
            user__premium_user=False
        ).exclude(user=user).filter(status='COMPLETED')

    results = results.prefetch_related('quizzes')

    data = []
    for result in results:
        data.append({
            'id': result.id,
            'document_title': result.document_title,
            'audio_summary': result.audio_summary.url if result.audio_summary else None,
            'pdf_report': result.pdf_report.url if result.pdf_report else None,
            'Quiz': list(result.quizzes.values('id', 'name')),
            'created_at': result.created_at.isoformat() if result.created_at else None,
        })

    return Response(data)
    
