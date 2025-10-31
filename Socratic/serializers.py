from rest_framework import serializers
from .models import ProcessingResult
import os

class DocumentProcessingSerializer(serializers.Serializer):
    study_material = serializers.FileField(
        max_length=100,
        allow_empty_file=False,
        write_only=True,
        help_text="PDF or Word document containing study material"
    )
    past_questions = serializers.FileField(
        required=False,
        allow_empty_file=False,
        write_only=True,
        help_text="Optional: PDF, Word, or clear images of past questions"
    )
    
    document_title = serializers.CharField(max_length=255, required=False)
    
    def validate_study_material(self, value):
        """Validate study material file"""
        return self._validate_file(value, ['.pdf', '.docx'])
    
    def validate_past_questions(self, value):
        """Validate past questions file"""
        if value: 
            return self._validate_file(value, ['.pdf', '.docx', '.jpg', '.jpeg', '.png'])
        return value
    
    def _validate_file(self, value, allowed_extensions):
        """Generic file validation"""
        ext = os.path.splitext(value.name)[1].lower()
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
            )
        
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('File size cannot exceed 10MB.')
        
        return value
    
    def validate(self, data):
        """Set document title from filename if not provided"""
        if not data.get('document_title'):
            filename = data['study_material'].name
            title = os.path.splitext(filename)[0]
            data['document_title'] = title
        return data

class ProcessingResultSerializer(serializers.ModelSerializer):
    processing_time_formatted = serializers.SerializerMethodField()
    audio_download_url = serializers.SerializerMethodField()
    pdf_download_url = serializers.SerializerMethodField()
    has_past_questions_context = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingResult
        fields = [
            'id',
            'document_title',
            'used_past_questions',
            'has_past_questions_context',
            'summary',
            'questions_answers',
            'audio_download_url',
            'pdf_download_url',
            'processing_time_formatted',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_processing_time_formatted(self, obj):
        if obj.processing_time:
            return f"{obj.processing_time:.2f} seconds"
        return "Not recorded"
    
    def get_audio_download_url(self, obj):
        if obj.audio_summary:
            return obj.audio_summary.url
        return None
    
    def get_pdf_download_url(self, obj):
        if obj.pdf_report:
            return obj.pdf_report.url
        return None
    
    def get_has_past_questions_context(self, obj):
        return bool(obj.past_questions_context)
    
class MinimalProcessingResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingResult
        fields = [
            'id',
            'document_title',
            'created_at',
            'used_past_questions',
            'created_at',
            'processing_time',
            'quiz_generated',
            'pdf_generated',
            'audio_generated',
        ]
        read_only_fields = fields