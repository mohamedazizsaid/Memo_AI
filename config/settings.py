"""
MemoAi — Django Settings
Production-ready configuration with environment-based overrides.
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# ─────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ─────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'cloudinary',
    'cloudinary_storage',
    # MemoAi apps
    'common',
    'accounts',
    'journal',
    'media_app',
    'ai',
    'persons',
    'tags',
    'notifications',
]

# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        # Django 5.2 wraps the loaders in the cached loader unconditionally when
        # 'loaders' is omitted, so template edits would not show up until the
        # server restarts. Listing the loaders explicitly keeps development
        # instant while still resolving app-level templates.
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notifications_context',
                'accounts.context_processors.language_context',
                'accounts.context_processors.user_experience_context',
            ],
            'builtins': [
                'accounts.templatetags.memoai_i18n',
                'common.templatetags.memo_filters',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ─────────────────────────────────────────────
# Database — PostgreSQL (default) or SQLite (dev fallback)
# ─────────────────────────────────────────────
DB_ENGINE = config('DB_ENGINE', default='postgresql')
if DB_ENGINE == 'sqlite' or config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='memoai'),
            'USER': config('DB_USER', default='memoai_user'),
            'PASSWORD': config('DB_PASSWORD', default='memoai_password'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        },
        'sqlite': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    }

# ─────────────────────────────────────────────
# Cache — Redis (default) or LocMem (dev fallback)
# ─────────────────────────────────────────────
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
USE_REDIS = config('USE_REDIS', default=True, cast=bool)

if USE_REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
            },
            'KEY_PREFIX': 'memoai',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'memoai-local-cache',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# ─────────────────────────────────────────────
# Authentication — Custom User Model
# ─────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Redirect URL for @login_required (template views)
LOGIN_URL = '/comptes/connexion/'
LOGIN_REDIRECT_URL = '/journal/'
LOGOUT_REDIRECT_URL = '/comptes/connexion/'

# ─────────────────────────────────────────────
# REST Framework
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardResultsPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '200/minute',
        'ai': '20/minute',
    },
}

# ─────────────────────────────────────────────
# JWT Configuration
# ─────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://localhost:3000',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://localhost:3000',
    cast=Csv()
)

# ─────────────────────────────────────────────
# Cloudinary Storage
# ─────────────────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# Django 5.1+ removed DEFAULT_FILE_STORAGE; STORAGES is the supported API.
# The default backend keeps Cloudinary as the only storage for user files,
# while `common.cloud_media` uploads explicitly (and never falls back to disk).
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Folder root used for every asset MemoAI pushes to Cloudinary
# (generated illustrations, etc.).
CLOUDINARY_MEDIA_FOLDER = config('CLOUDINARY_MEDIA_FOLDER', default='memoai')

# ─────────────────────────────────────────────
# Static & Media Files
# ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Upload limits
MAX_UPLOAD_SIZE_MB = config('MAX_UPLOAD_SIZE_MB', default=50, cast=int)
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm', 'audio/mp4', 'audio/m4a']

# ─────────────────────────────────────────────
# Celery — Async Tasks
# ─────────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = config('CELERY_ALWAYS_EAGER', default=not USE_REDIS, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = config('CELERY_EAGER_PROPAGATES', default=True, cast=bool)

if not USE_REDIS or CELERY_TASK_ALWAYS_EAGER:
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
else:
    CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True


# ─────────────────────────────────────────────
# Celery Beat — Scheduled Tasks
# ─────────────────────────────────────────────
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'daily-memory-reminder': {
        'task': 'notifications.tasks.send_daily_memory_reminder',
        'schedule': crontab(hour=9, minute=0),  # Every day at 9 AM
    },
    'weekly-summary': {
        'task': 'notifications.tasks.send_weekly_summary',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Every Monday
    },
    'monthly-memory-review': {
        'task': 'notifications.tasks.send_monthly_memory_review',
        'schedule': crontab(hour=10, minute=0, day_of_month=1),  # First of each month
    },
    'cleanup-pending-ai-tasks': {
        'task': 'ai.tasks.cleanup_stale_tasks',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}

# ─────────────────────────────────────────────
# AI Services
# ─────────────────────────────────────────────
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
# gemini-1.5-* has been retired by Google — gemini-2.5-flash is the current
# fast general-purpose model that returns our structured JSON summary.
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.5-flash')
GEMINI_VISION_MODEL = config('GEMINI_VISION_MODEL', default='gemini-2.5-flash')

HUGGINGFACE_API_KEY = config('HUGGINGFACE_API_KEY', default='')
HUGGINGFACE_ASR_MODEL = config('HUGGINGFACE_ASR_MODEL', default='openai/whisper-large-v3')
HUGGINGFACE_SENTIMENT_MODEL = config('HUGGINGFACE_SENTIMENT_MODEL', default='cardiffnlp/twitter-roberta-base-sentiment-latest')
HUGGINGFACE_IMAGE_MODEL = config('HUGGINGFACE_IMAGE_MODEL', default='stabilityai/stable-diffusion-xl-base-1.0')

# ─────────────────────────────────────────────
# Image generation — Pollinations (100% free, key-less)
# ─────────────────────────────────────────────
# Pollinations renders an image from the URL of a prompt: no API key, no quota.
# https://image.pollinations.ai/prompt/<url-encoded prompt>
POLLINATIONS_BASE_URL = config('POLLINATIONS_BASE_URL', default='https://image.pollinations.ai/prompt')
IMAGE_GENERATION_MODEL = config('IMAGE_GENERATION_MODEL', default='flux')
IMAGE_GENERATION_WIDTH = config('IMAGE_GENERATION_WIDTH', default=896, cast=int)
IMAGE_GENERATION_HEIGHT = config('IMAGE_GENERATION_HEIGHT', default=576, cast=int)

# ─────────────────────────────────────────────
# Face recognition — face-api.js assets served locally
# ─────────────────────────────────────────────
# Models are downloaded to static/vendor/face-api/weights and loaded by the
# browser (client-side detection). The threshold below is the euclidean
# distance below which two 128-d descriptors are considered the same person.
FACE_API_WEIGHTS_URL = config('FACE_API_WEIGHTS_URL', default='/static/vendor/face-api/weights')

# Face Recognition
FACE_RECOGNITION_ENABLED = config('FACE_RECOGNITION_ENABLED', default=True, cast=bool)
FACE_RECOGNITION_CONFIDENCE_THRESHOLD = config('FACE_RECOGNITION_CONFIDENCE_THRESHOLD', default=0.6, cast=float)

# AI Mock mode (for tests / no API keys)
AI_MOCK_MODE = config('AI_MOCK_MODE', default=False, cast=bool)

# ─────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='MemoAi <noreply@memoai.app>')
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=15, cast=int)

# ─────────────────────────────────────────────
# Pexels — online photo picker (journal editor)
# ─────────────────────────────────────────────
PEXELS_API_KEY = config('PEXELS_API_KEY', default='')
PEXELS_API_BASE_URL = config('PEXELS_API_BASE_URL', default='https://api.pexels.com/v1')

# ─────────────────────────────────────────────
# Places - "Add a location" (OpenStreetMap / Nominatim, keyless)
# ─────────────────────────────────────────────
PLACES_API_BASE_URL = config('PLACES_API_BASE_URL', default='https://nominatim.openstreetmap.org')

# ─────────────────────────────────────────────
# Internationalization
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='WARNING'),
            'propagate': False,
        },
        'memoai': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
