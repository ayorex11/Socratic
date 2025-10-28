from django.db import models
from Account.models import User
class LogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=50)
    status_code = models.CharField(max_length=10, blank=True, null=True)
    message = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_for_log_entry')

    class Meta:
        db_table = 'log_entries'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.level}: {self.message[:50]}..."