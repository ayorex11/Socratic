import os
import subprocess
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from logs.models import LogEntry 
from .models import ProcessingResult
from .utils.document_processor import DocumentProcessor
from .utils.ai_processor import PremiumAIProcessor
from .utils.free_ai_processor import AIProcessor
from .utils.text_to_speech import TextToSpeech
from .utils.pdf_generator import AdvancedPDFGenerator
from .utils.quiz_generator import AdvancedQuizGenerator, AIPoweredQuizGenerator
from .utils.file_helpers import _save_temp_file, _cleanup_temp_file
import time

User = get_user_model()

@shared_task(bind=True)
def process_document_task(self, result_id, user_id, study_temp_path, past_questions_temp_path, 
                          study_material_name, document_title):
    start_time = time.time()
    audio_path = None 
    result = None 

    try:
        user = User.objects.get(id=user_id)
        result = ProcessingResult.objects.get(id=result_id)
        
        result.status = 'PROCESSING'
        result.save()
        
        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Normal', status_code='200',
            message=f'Task {self.request.id} started processing for result ID {result_id}'
        )


        # Extract study material text with enhanced error handling
        try:
            study_file_type = DocumentProcessor.get_file_type(study_material_name)
            print(f"Processing study material: {study_material_name}, type: {study_file_type}")
            
            # Verify temp file exists and has content
            if not os.path.exists(study_temp_path):
                raise Exception(f"Study material temp file not found: {study_temp_path}")
            
            file_size = os.path.getsize(study_temp_path)
            print(f"Study material file size: {file_size} bytes")
            
            if file_size == 0:
                raise Exception("Study material temp file is empty")
            
            study_text = DocumentProcessor.extract_text(study_temp_path, study_file_type)
            print(f"Extracted study text: {len(study_text)} characters")
            
            if not study_text or len(study_text.strip()) < 50:
                raise Exception("Insufficient text extracted from study material")
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Successfully extracted {len(study_text)} characters from study material'
            )
            
        except Exception as e:
            error_msg = f'Study material extraction failed: {str(e)}'
            print(error_msg)
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Error', status_code='500',
                message=error_msg
            )
            raise
        
        # Extract past questions text with graceful error handling
        past_questions_text = ""
        if past_questions_temp_path and os.path.exists(past_questions_temp_path):
            try:
                past_questions_file_type = DocumentProcessor.get_file_type(past_questions_temp_path)
                print(f"Processing past questions, type: {past_questions_file_type}")
                
                # Verify temp file has content
                file_size = os.path.getsize(past_questions_temp_path)
                print(f"Past questions file size: {file_size} bytes")
                
                if file_size == 0:
                    raise Exception("Past questions temp file is empty")
                
                past_questions_text = DocumentProcessor.extract_text(past_questions_temp_path, past_questions_file_type)
                print(f"Extracted past questions: {len(past_questions_text)} characters")
                
                if past_questions_text and len(past_questions_text.strip()) > 20:
                    LogEntry.objects.create(
                        user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                        message=f'Successfully extracted {len(past_questions_text)} characters from past questions'
                    )
                else:
                    print("WARNING: Minimal text extracted from past questions")
                    past_questions_text = ""
                    
            except Exception as e:
                error_msg = f'Past questions extraction failed: {str(e)}'
                print(error_msg)
                LogEntry.objects.create(
                    user=user, timestamp=timezone.now(), level='Error', status_code='500',
                    message=error_msg
                )
                # Don't fail the whole task, just continue without past questions
                past_questions_text = ""
        elif past_questions_temp_path:
            print(f"Past questions file not found at: {past_questions_temp_path}")
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message='Past questions file path provided but file not found'
            )
            
        # AI Processing
        try:
            if user.premium_user:
                summary, qa_data = PremiumAIProcessor.generate_enhanced_content(study_text, past_questions_text)
            else:
                summary, qa_data = AIProcessor.generate_enhanced_content(study_text, past_questions_text)
            
            result.past_questions_context = past_questions_text
            result.summary = summary
            result.questions_answers = qa_data
            result.save()
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated AI content for result ID {result_id}'
            )
        except Exception as e:
            error_msg = f'AI content generation failed: {str(e)}'
            print(error_msg)
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Error', status_code='500',
                message=error_msg
            )
            raise

        # Audio Generation
        try:
            audio_path = TextToSpeech.generate_audio(result.summary, f"audio_{result_id}")
            if audio_path:
                result.audio_summary.name = audio_path  # Use .name to set R2 path reference
                result.audio_generated = True
            else:
                result.audio_summary = None
                result.audio_generated = False
            result.save()

            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated audio for result ID {result_id}'
            )
        except Exception as e:
            result.audio_summary = None 
            result.audio_generated = False
            result.save()
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED audio generation: {str(e)}'
            )

        # PDF Generation
        try:
            pdf_path = AdvancedPDFGenerator.generate_report(processing_result=result, output_filename=f"report_{result_id}")
            if pdf_path:
                result.pdf_report.name = pdf_path  # Use .name to set R2 path reference
                result.pdf_generated = True
            else:
                result.pdf_report = None
                result.pdf_generated = False
            result.save()
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated PDF for result ID {result_id}'
            )
        except Exception as e:
            result.pdf_report = None
            result.pdf_generated = False
            result.save()
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED PDF generation: {str(e)}'
            )

        # Quiz Generation
        try:
            if user.premium_user:
                AdvancedQuizGenerator.generate_enhanced_quiz(result)
            else:
                AIPoweredQuizGenerator.generate_quiz_from_processing_result(result)
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated quiz for result ID {result_id}'
            )
        except Exception as e:
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED quiz generation: {str(e)}'
            )

        end_time = time.time()
        result.processing_time = end_time - start_time
        result.status = 'COMPLETED'
        result.save()

        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Normal', status_code='200',
            message=f'Task {self.request.id} successfully completed processing for result ID {result_id} in {result.processing_time:.2f}s'
        )
        
    except Exception as e:
        error_msg = f'Task {self.request.id} FAILED: {str(e)}'
        print(error_msg)
        
        if result:
            try:
                result.status = 'FAILED'
                result.audio_generated = False
                result.pdf_generated = False
                result.save() 
            except Exception as save_error:
                print(f"Failed to update result status: {save_error}")
        
        try:
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Error', status_code='500',
                message=error_msg
            )
        except Exception as log_error:
            print(f"Failed to create log entry: {log_error}")
            
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    finally:
        # Cleanup temp files
        try:
            _cleanup_temp_file(study_temp_path)
            if past_questions_temp_path:
                _cleanup_temp_file(past_questions_temp_path)
            print("Temp files cleaned up successfully")
        except Exception as cleanup_error:
            print(f"Cleanup error: {cleanup_error}")