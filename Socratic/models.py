from django.db import models
import uuid
from django.core.files.storage import default_storage
from Account.models import User

class ProcessingResult(models.Model):

    STAGE_CHOICES = [
        ('pending', 'Pending'),
        ('extracting_text', 'Extracting Text'),
        ('generating_summary', 'Generating Summary'),
        ('creating_pdf', 'Creating PDF'),
        ('generating_audio', 'Generating Audio'),
        ('creating_quiz', 'Creating Quiz'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processing_results')
    document_title = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    used_past_questions = models.BooleanField(default=False)
    past_questions_context = models.TextField(blank=True, null=True)
    summary = models.TextField()
    questions_answers = models.JSONField(default=dict)
    audio_summary = models.FileField(upload_to='audio/', blank=True, null=True)
    pdf_report = models.FileField(upload_to='reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(null=True, blank=True)
    quiz_generated = models.BooleanField(default=False)
    pdf_generated = models.BooleanField(default=False)
    audio_generated = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default='PROCESSING')
    processing_stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default='pending')
    stage_progress = models.IntegerField(default=0)
    stage_message = models.CharField(max_length=255, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'processing_results'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document_title} - {self.created_at}"
    
    def update_stage(self, stage, progress=None, message=None):
        """Helper method to update processing stage details."""
        self.processing_stage = stage
        if progress is not None:
            self.stage_progress = progress
        if message is not None:
            self.stage_message = message
        self.save(update_fields=['processing_stage', 'stage_progress', 'stage_message'])
    
    def delete(self, *args, **kwargs):
        # Use Django's storage to delete files from R2
        if self.audio_summary:
            default_storage.delete(self.audio_summary.name)
        if self.pdf_report:
            default_storage.delete(self.pdf_report.name)
        super().delete(*args, **kwargs)