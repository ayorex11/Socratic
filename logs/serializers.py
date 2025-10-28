from rest_framework import serializers
from .models import LogEntry

class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = ['id', 'timestamp', 'level', 'status_code', 'message', 'user']
        read_only_fields = ['id', 'timestamp', 'user']

class DateFilterSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()