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
        
        # STAGE 1: Starting Processing
        result.status = 'PROCESSING'
        result.save()
        result.update_stage('extracting_text', progress=10, message='Starting text extraction...')
        
        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Normal', status_code='200',
            message=f'Task {self.request.id} started processing for result ID {result_id}'
        )

        # STAGE 2: Extract study material text
        try:
            study_file_type = DocumentProcessor.get_file_type(study_material_name)
            print(f"Processing study material: {study_material_name}, type: {study_file_type}")
            
            result.update_stage('extracting_text', progress=20, message=f'Extracting from {study_file_type} file...')
            
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
            
            result.update_stage('extracting_text', progress=35, message=f'Extracted {len(study_text)} characters')
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Successfully extracted {len(study_text)} characters from study material'
            )
            
        except Exception as e:
            error_msg = f'Study material extraction failed: {str(e)}'
            print(error_msg)
            result.update_stage('failed', progress=0, message=error_msg)
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Error', status_code='500',
                message=error_msg
            )
            raise
        
        # STAGE 3: Extract past questions (optional)
        past_questions_text = ""
        if past_questions_temp_path and os.path.exists(past_questions_temp_path):
            try:
                result.update_stage('extracting_text', progress=45, message='Processing past questions...')
                
                past_questions_file_type = DocumentProcessor.get_file_type(past_questions_temp_path)
                print(f"Processing past questions, type: {past_questions_file_type}")
                
                file_size = os.path.getsize(past_questions_temp_path)
                print(f"Past questions file size: {file_size} bytes")
                
                if file_size == 0:
                    raise Exception("Past questions temp file is empty")
                
                past_questions_text = DocumentProcessor.extract_text(past_questions_temp_path, past_questions_file_type)
                print(f"Extracted past questions: {len(past_questions_text)} characters")
                
                if past_questions_text and len(past_questions_text.strip()) > 20:
                    result.update_stage('extracting_text', progress=50, message='Past questions extracted successfully')
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
                past_questions_text = ""
            
        # STAGE 4: AI Processing - Generate Summary and Q&A
        try:
            result.update_stage('generating_summary', progress=55, message='Analyzing content with AI...')
            
            if user.premium_user:
                summary, qa_data = PremiumAIProcessor.generate_enhanced_content(study_text, past_questions_text)
            else:
                summary, qa_data = AIProcessor.generate_enhanced_content(study_text, past_questions_text)
            
            result.past_questions_context = past_questions_text
            result.summary = summary
            result.questions_answers = qa_data
            result.save()
            
            result.update_stage('generating_summary', progress=65, message='AI analysis completed')
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated AI content for result ID {result_id}'
            )
        except Exception as e:
            error_msg = f'AI content generation failed: {str(e)}'
            print(error_msg)
            result.update_stage('failed', progress=0, message=error_msg)
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Error', status_code='500',
                message=error_msg
            )
            raise

        # STAGE 5: PDF Generation
        try:
            result.update_stage('creating_pdf', progress=70, message='Generating PDF report...')
            
            pdf_path = AdvancedPDFGenerator.generate_report(processing_result=result, output_filename=f"report_{result_id}")
            if pdf_path:
                result.pdf_report.name = pdf_path
                result.pdf_generated = True
            else:
                result.pdf_report = None
                result.pdf_generated = False
            result.save()
            
            result.update_stage('creating_pdf', progress=75, message='PDF generated successfully')
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated PDF for result ID {result_id}'
            )
        except Exception as e:
            result.pdf_report = None
            result.pdf_generated = False
            result.save()
            result.update_stage('creating_pdf', progress=75, message=f'PDF generation failed: {str(e)}')
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED PDF generation: {str(e)}'
            )

        # STAGE 6: Audio Generation
        try:
            result.update_stage('generating_audio', progress=80, message='Creating audio summary...')
            
            audio_path = TextToSpeech.generate_audio(result.summary, f"audio_{result_id}")
            if audio_path:
                result.audio_summary.name = audio_path
                result.audio_generated = True
            else:
                result.audio_summary = None
                result.audio_generated = False
            result.save()
            
            result.update_stage('generating_audio', progress=85, message='Audio generated successfully')

            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated audio for result ID {result_id}'
            )
        except Exception as e:
            result.audio_summary = None 
            result.audio_generated = False
            result.save()
            result.update_stage('generating_audio', progress=85, message=f'Audio generation failed: {str(e)}')
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED audio generation: {str(e)}'
            )

        # STAGE 7: Quiz Generation
        try:
            result.update_stage('creating_quiz', progress=90, message='Generating practice quiz...')
            
            if user.premium_user:
                AdvancedQuizGenerator.generate_enhanced_quiz(result)
            else:
                AIPoweredQuizGenerator.generate_quiz_from_processing_result(result)
            
            result.update_stage('creating_quiz', progress=95, message='Quiz generated successfully')
            
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated quiz for result ID {result_id}'
            )
        except Exception as e:
            result.update_stage('creating_quiz', progress=95, message=f'Quiz generation failed: {str(e)}')
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED quiz generation: {str(e)}'
            )

        # STAGE 8: Completion
        end_time = time.time()
        result.processing_time = end_time - start_time
        result.status = 'COMPLETED'
        result.save()
        result.update_stage('completed', progress=100, message='All processing completed successfully!')

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
                result.update_stage('failed', progress=0, message=str(e))
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