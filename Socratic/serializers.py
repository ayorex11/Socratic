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


class MinimalProcessingResultSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views and status polling.
    This is what your frontend polls every 3 seconds.
    """
    stage_label = serializers.SerializerMethodField()
    is_processing = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingResult
        fields = [
            'id',
            'document_title',
            'created_at',
            'used_past_questions',
            'processing_time',
            'quiz_generated',
            'pdf_generated',
            'audio_generated',
            'status',
            'processing_stage',        # e.g., 'creating_pdf'
            'stage_progress',          # e.g., 70
            'stage_message',           # e.g., 'Generating PDF report...'
            'stage_label',             # e.g., 'Creating PDF' (computed)
            'is_processing',           # e.g., True/False (computed)
        ]
        read_only_fields = fields
    
    def get_stage_label(self, obj):
        """Get human-readable stage label"""
        return obj.get_processing_stage_display() if obj.processing_stage else 'Unknown'
    
    def get_is_processing(self, obj):
        """Check if document is currently being processed"""
        return obj.status == 'PROCESSING' and obj.processing_stage not in ['completed', 'failed']


class ProcessingResultSerializer(serializers.ModelSerializer):
    """
    Full serializer for detailed document views.
    Includes all document data plus stage tracking.
    """
    processing_time_formatted = serializers.SerializerMethodField()
    audio_download_url = serializers.SerializerMethodField()
    pdf_download_url = serializers.SerializerMethodField()
    has_past_questions_context = serializers.SerializerMethodField()
    stage_label = serializers.SerializerMethodField()
    is_processing = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    
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
            'created_at',
            'status',
            'processing_stage',
            'stage_progress',
            'stage_message',
            'stage_label',
            'is_processing',
            'completion_percentage',
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
    
    def get_stage_label(self, obj):
        """Get human-readable stage label"""
        return obj.get_processing_stage_display() if obj.processing_stage else 'Unknown'
    
    def get_is_processing(self, obj):
        """Check if document is currently being processed"""
        return obj.status == 'PROCESSING' and obj.processing_stage not in ['completed', 'failed']
    
    def get_completion_percentage(self, obj):
        """
        Calculate overall completion percentage.
        This is useful for overall progress indicators.
        """
        if obj.status == 'COMPLETED':
            return 100
        elif obj.status == 'FAILED':
            return 0
        else:
            if obj.stage_progress:
                return obj.stage_progress
            
            stage_weights = {
                'pending': 0,
                'extracting_text': 15,
                'generating_summary': 40,
                'creating_pdf': 60,
                'generating_audio': 80,
                'creating_quiz': 90,
                'completed': 100,
                'failed': 0,
            }
            return stage_weights.get(obj.processing_stage, 0)


class ProcessingStageSerializer(serializers.Serializer):
    """
    Dedicated serializer for real-time stage updates.
    Use this if you want a lightweight endpoint just for stage checking.
    """
    id = serializers.UUIDField()
    processing_stage = serializers.CharField()
    stage_progress = serializers.IntegerField()
    stage_message = serializers.CharField()
    stage_label = serializers.CharField()
    status = serializers.CharField()
    is_processing = serializers.BooleanField()