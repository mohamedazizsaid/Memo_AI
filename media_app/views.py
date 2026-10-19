"""
MemoAi — Media Views
Secure file upload to Cloudinary with validation.
"""

import logging
from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import IsOwner
from journal.models import JournalEntry
from .models import Media
from .serializers import MediaSerializer

logger = logging.getLogger('memoai')

ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm', 'audio/mp4', 'audio/m4a']


def validate_file(file, media_type):
    """Validate file type and size."""
    content_type = file.content_type
    max_size = settings.MAX_UPLOAD_SIZE

    if media_type == 'IMAGE' and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type: {content_type}")
    elif media_type == 'AUDIO' and content_type not in ALLOWED_AUDIO_TYPES:
        raise ValueError(f"Unsupported audio type: {content_type}")

    if file.size > max_size:
        raise ValueError(f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB")


def upload_to_cloudinary(file, media_type, user_id):
    """Upload file to Cloudinary and return URL and public_id (no local disk)."""
    from common.cloud_media import upload_media

    return upload_media(file, media_type, user_id, kind=None)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_media(request):
    """
    Upload a media file to Cloudinary.
    POST /api/media/upload/
    """
    file = request.FILES.get('file')
    media_type = request.data.get('media_type', '').upper()
    entry_id = request.data.get('entry_id')

    if not file:
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
    if media_type not in ['IMAGE', 'AUDIO']:
        return Response({'error': 'Invalid media_type.'}, status=status.HTTP_400_BAD_REQUEST)
    if not entry_id:
        return Response({'error': 'entry_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Verify entry belongs to user
    try:
        entry = JournalEntry.objects.get(pk=entry_id, user=request.user)
    except JournalEntry.DoesNotExist:
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Validate file
    try:
        validate_file(file, media_type)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Upload to Cloudinary
        url, public_id = upload_to_cloudinary(file, media_type, str(request.user.id))

        # Create media record
        media = Media.objects.create(
            entry=entry,
            media_type=media_type,
            storage_url=url,
            cloudinary_public_id=public_id,
            mime_type=file.content_type,
            file_size=file.size,
            original_filename=file.name,
        )

        # Trigger appropriate processing task
        if media_type == 'AUDIO':
            from ai.tasks import process_audio_media
            task = process_audio_media.delay(str(media.id))
            media.processing_task_id = task.id
            media.processing_status = 'processing'
            media.save(update_fields=['processing_task_id', 'processing_status'])
        elif media_type == 'IMAGE':
            from ai.tasks import process_image_media
            task = process_image_media.delay(str(media.id))
            media.processing_task_id = task.id
            media.processing_status = 'processing'
            media.save(update_fields=['processing_task_id', 'processing_status'])

        return Response(
            MediaSerializer(media).data,
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return Response(
            {'error': 'Upload failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_media(request, pk):
    """Delete a media file from Cloudinary and database."""
    try:
        media = Media.objects.select_related('entry').get(pk=pk)
        # Ensure user owns the entry
        if media.entry.user != request.user:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Delete from Cloudinary
        if media.cloudinary_public_id:
            try:
                import cloudinary.uploader
                resource_type = 'video' if media.media_type == 'AUDIO' else 'image'
                cloudinary.uploader.destroy(
                    media.cloudinary_public_id,
                    resource_type=resource_type
                )
            except Exception as e:
                logger.warning(f"Cloudinary delete failed: {e}")

        media.delete()
        return Response({'success': True, 'message': 'Media deleted.'})

    except Media.DoesNotExist:
        return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def entry_media(request, entry_id):
    """List all media for a specific entry."""
    try:
        entry = JournalEntry.objects.get(pk=entry_id, user=request.user)
        media = entry.media.all()
        return Response(MediaSerializer(media, many=True).data)
    except JournalEntry.DoesNotExist:
        return Response({'error': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_gallery(request):
    """Get all images for the current user (gallery view)."""
    media = Media.objects.filter(
        entry__user=request.user,
        media_type='IMAGE'
    ).select_related('entry').order_by('-created_at')

    # Optional filter by entry
    entry_id = request.query_params.get('entry_id')
    if entry_id:
        media = media.filter(entry_id=entry_id)

    from common.pagination import StandardResultsPagination
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(media, request)
    return paginator.get_paginated_response(MediaSerializer(page, many=True).data)
