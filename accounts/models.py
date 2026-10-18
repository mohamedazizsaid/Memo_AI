"""
MemoAi — Custom User Model
Extended Django user with profile and preferences.
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as unique identifier.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    avatar = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.email[0].upper()


class UserPreferences(models.Model):
    """
    User preferences: theme, language, notifications.
    """
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('night', 'Night'),
        ('system', 'System'),
    ]
    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    # Display
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='fr')
    reduce_motion = models.BooleanField(default=False)

    # Notifications
    daily_reminder_enabled = models.BooleanField(default=True)
    daily_reminder_time = models.TimeField(default='09:00')
    weekly_summary_enabled = models.BooleanField(default=True)
    monthly_review_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)

    # AI Features
    ai_summaries_enabled = models.BooleanField(default=True)
    sentiment_analysis_enabled = models.BooleanField(default=True)
    image_generation_enabled = models.BooleanField(default=True)
    face_recognition_consent = models.BooleanField(default=False)
    face_recognition_consent_date = models.DateTimeField(null=True, blank=True)

    # Privacy
    auto_delete_face_embeddings = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_user_preferences'

    def __str__(self):
        return f"Preferences({self.user.email})"

    def grant_face_recognition_consent(self):
        self.face_recognition_consent = True
        self.face_recognition_consent_date = timezone.now()
        self.save(update_fields=['face_recognition_consent', 'face_recognition_consent_date'])

    def revoke_face_recognition_consent(self):
        self.face_recognition_consent = False
        self.face_recognition_consent_date = None
        self.save(update_fields=['face_recognition_consent', 'face_recognition_consent_date'])


class PasswordResetToken(models.Model):
    """Password reset tokens with expiry."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'accounts_password_reset_tokens'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired
