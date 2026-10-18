"""
MemoAi — Notifications Views
List, mark as read, and manage user notifications.
"""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    List notifications for current user.
    Query param ?unread_only=true filters to unread only.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread_only = self.request.query_params.get('unread_only')
        if unread_only and unread_only.lower() in ['true', '1']:
            qs = qs.filter(is_read=False)
        return qs[:100]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            'unread_count': unread_count,
            'results': serializer.data,
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """Mark a single notification as read."""
    try:
        notif = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=['is_read', 'read_at'])

    return Response({'success': True, 'notification': NotificationSerializer(notif).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all unread notifications for current user as read."""
    now = timezone.now()
    updated_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).update(is_read=True, read_at=now)

    return Response({
        'success': True,
        'marked_read_count': updated_count,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, pk):
    """Delete a single notification."""
    try:
        notif = Notification.objects.get(pk=pk, user=request.user)
        notif.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
