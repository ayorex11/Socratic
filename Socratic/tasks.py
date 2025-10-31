import os
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

        study_file_type = DocumentProcessor.get_file_type(study_material_name)
        study_text = DocumentProcessor.extract_text(study_temp_path, study_file_type)
        
        past_questions_text = ""
        if past_questions_temp_path and os.path.exists(past_questions_temp_path):
            past_questions_file_type = DocumentProcessor.get_file_type(past_questions_temp_path)
            past_questions_text = DocumentProcessor.extract_text(past_questions_temp_path, past_questions_file_type)
            
        if user.premium_user:
            summary, qa_data = PremiumAIProcessor.generate_enhanced_content(study_text, past_questions_text)
        else:
            summary, qa_data = AIProcessor.generate_enhanced_content(study_text, past_questions_text)

        result.past_questions_context = past_questions_text
        result.summary = summary
        result.questions_answers = qa_data
        result.save()

        try:
            audio_path = TextToSpeech.generate_audio(result.summary, f"audio_{result_id}")
            result.audio_summary = audio_path
            result.audio_generated = True
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Normal', status_code='200',
                message=f'Task {self.request.id} successfully generated audio for result ID {result_id}'
            )
        except Exception as e:
            result.audio_summary = None 
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED audio generation: {str(e)}'
            )

        try:
            pdf_path = AdvancedPDFGenerator.generate_report(processing_result=result, output_filename=f"report_{result_id}")
            result.pdf_report = pdf_path
            result.pdf_generated = True
        except Exception as e:
            LogEntry.objects.create(
                user=user, timestamp=timezone.now(), level='Warning', status_code='400',
                message=f'Task {self.request.id} FAILED PDF generation: {str(e)}'
            )

        try:
            if user.premium_user:
                AdvancedQuizGenerator.generate_enhanced_quiz(result)
            else:
                AIPoweredQuizGenerator.generate_quiz_from_processing_result(result)
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
            message=f'Task {self.request.id} successfully completed processing for result ID {result_id}'
        )
        
    except Exception as e:
        if result:
            try:
                result.status = 'FAILED'
                result.save() 
            except Exception:
                pass
            
        LogEntry.objects.create(
            user=user, timestamp=timezone.now(), level='Error', status_code='500',
            message=f'Task {self.request.id} FAILED: {str(e)}'
        )
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    finally:
        _cleanup_temp_file(study_temp_path)
        if past_questions_temp_path:
            _cleanup_temp_file(past_questions_temp_path)