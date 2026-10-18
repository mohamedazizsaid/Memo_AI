"""
MemoAi — Accounts Views
Authentication, registration, profile management.
"""

import logging
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserPreferences, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer,
    MemoAiTokenObtainPairSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserPreferencesSerializer,
    UserPreferencesUpdateSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

logger = logging.getLogger('memoai')
User = get_user_model()


class LoginThrottle(AnonRateThrottle):
    rate = '10/minute'


class RegisterView(generics.CreateAPIView):
    """Register a new user."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens immediately after registration
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        return Response({
            'success': True,
            'access': access_token,
            'refresh': refresh_token,
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'access': access_token,
                'refresh': refresh_token,
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """Login and receive JWT tokens."""
    serializer_class = MemoAiTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.get('access')
            refresh = response.data.get('refresh')
            user_data = response.data.get('user')
            return Response({
                'success': True,
                'access': access,
                'refresh': refresh,
                'tokens': {
                    'access': access,
                    'refresh': refresh,
                },
                'user': user_data,
            })
        return response



class LogoutView(generics.GenericAPIView):
    """Logout and blacklist the refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'success': True, 'message': 'Logged out successfully.'})
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({'success': True, 'message': 'Logged out.'})


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get and update current user profile."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)
        # Return full profile after update
        return Response(UserProfileSerializer(request.user).data)


class PreferencesView(generics.RetrieveUpdateAPIView):
    """Get and update user preferences."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserPreferencesUpdateSerializer
        return UserPreferencesSerializer

    def get_object(self):
        prefs, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        return prefs

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class ChangePasswordView(generics.GenericAPIView):
    """Change current user password."""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'success': True, 'message': 'Password changed successfully.'})


class PasswordResetRequestView(generics.GenericAPIView):
    """Request a password reset email."""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            # Generate secure token
            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=timezone.now() + timedelta(hours=2),
            )
            # TODO: Send email with reset link
            logger.info(f"Password reset requested for {email}")
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        # Always return success to prevent email enumeration
        return Response({
            'success': True,
            'message': 'If an account with that email exists, a reset link has been sent.'
        })


class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm password reset with token."""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reset_token = PasswordResetToken.objects.get(
                token=serializer.validated_data['token']
            )
            if not reset_token.is_valid:
                return Response(
                    {'success': False, 'error': {'message': 'Token is invalid or expired.'}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user = reset_token.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            reset_token.used = True
            reset_token.save()
            return Response({'success': True, 'message': 'Password reset successfully.'})
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'success': False, 'error': {'message': 'Invalid token.'}},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grant_face_recognition_consent(request):
    """Grant consent for face recognition processing."""
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    prefs.grant_face_recognition_consent()
    return Response({'success': True, 'message': 'Face recognition consent granted.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_face_recognition_consent(request):
    """Revoke consent and delete all face embeddings."""
    from persons.models import Person
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    prefs.revoke_face_recognition_consent()

    # Delete all face embeddings for this user
    Person.objects.filter(user=request.user).update(face_embedding=None)
    logger.info(f"Face recognition consent revoked for user {request.user.id}")

    return Response({'success': True, 'message': 'Consent revoked and embeddings deleted.'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """Permanently delete user account and all associated data."""
    user = request.user
    user_id = str(user.id)
    user.delete()
    logger.info(f"Account deleted: {user_id}")
    return Response({'success': True, 'message': 'Account deleted permanently.'})
