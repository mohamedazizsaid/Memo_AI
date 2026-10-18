"""
MemoAi — AI Views
Direct AI operations: re-analysis, status checks.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from journal.models import JournalEntry
from .models import AIAnalysis
from .serializers import AIAnalysisSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_analysis_detail(request, entry_id):
    """Get AI analysis for a specific entry."""
    try:
        entry = JournalEntry.objects.get(pk=entry_id, user=request.user)
        analysis = entry.ai_analysis
        return Response(AIAnalysisSerializer(analysis).data)
    except JournalEntry.DoesNotExist:
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)
    except AIAnalysis.DoesNotExist:
        return Response({}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retrigger_ai(request, entry_id):
    """Re-trigger AI analysis for an entry."""
    try:
        entry = JournalEntry.objects.get(pk=entry_id, user=request.user)
    except JournalEntry.DoesNotExist:
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    from .tasks import analyze_entry
    task = analyze_entry.delay(str(entry.id))
    entry.ai_status = 'processing'
    entry.ai_task_id = task.id
    entry.save(update_fields=['ai_status', 'ai_task_id'])

    return Response({'success': True, 'task_id': task.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_image_for_entry(request, entry_id):
    """Manually trigger image generation for an entry."""
    try:
        entry = JournalEntry.objects.get(pk=entry_id, user=request.user)
    except JournalEntry.DoesNotExist:
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    from .tasks import generate_entry_image_task
    generate_entry_image_task.delay(str(entry.id))

    return Response({'success': True, 'message': 'Image generation started.'})
