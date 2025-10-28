from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import LogEntry
from .serializers import LogEntrySerializer, DateFilterSerializer
from drf_yasg.utils import swagger_auto_schema

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_log_entries(request):
    user = request.user
    """List all log entries"""
    logs = LogEntry.objects.all()
    if user.is_admin == False:
        return Response({"error": "You do not have permission to view logs."}, status=status.HTTP_403_FORBIDDEN)
    serializer = LogEntrySerializer(logs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_log_entry(request, pk):
    user = request.user
    """Get specific log entry by ID"""
    if user.is_admin == False:
        return Response({"error": "You do not have permission to view logs."}, status=status.HTTP_403_FORBIDDEN)
    try:
        log = LogEntry.objects.get(pk=pk)
        serializer = LogEntrySerializer(log)
        return Response(serializer.data)
    except LogEntry.DoesNotExist:
        return Response({"error": "Log entry not found."}, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])

def filter_log_entry_by_status_code(request, status):

    user = request.user
    """Get Log entries by status code"""
    if user.is_admin == False:
        return Response({"error": "You do not have permission to view logs."}, status=status.HTTP_403_FORBIDDEN)
    log = LogEntry.objects.filter(status_code = status)
    serializer = LogEntrySerializer(log, many=True)
    return Response(serializer.data)

@swagger_auto_schema(methods=['GET'], query_serializer=DateFilterSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def filter_by_time_range(request):
    user = request.user
    """Filter Log entries by time range"""
    if user.is_admin == False:
        return Response({"error": "You do not have permission to view logs."}, status=status.HTTP_403_FORBIDDEN)
    dates = DateFilterSerializer(data=request.query_params)
    dates.is_valid(raise_exception=True)
    start_date = dates.validated_data['start_date']
    end_date = dates.validated_data['end_date']
    try: 
        log = LogEntry.objects.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
        serializer = LogEntrySerializer(log, many=True)
        return Response(serializer.data)
    except LogEntry.DoesNotExist:
        return Response({'Log entries for given dates not found'}, status=status.HTTP_404_NOT_FOUND)


