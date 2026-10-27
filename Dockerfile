# ============================================================
# MemoAI — Dockerfile (production-ready, multi-stage)
# ============================================================

# ── Stage 1: Python dependencies builder ────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build essentials for psycopg2, librosa/soundfile and compiled packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ── Stage 2: Production runtime ─────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8000 \
    FRONTEND_URL=http://localhost:8000

WORKDIR $APP_HOME

# Runtime libs only (PostgreSQL, audio decoding with libsndfile/ffmpeg, healthcheck curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r memoai && useradd -r -g memoai memoai

# Copy pre-built wheels from builder and install
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy project source
COPY --chown=memoai:memoai . .

# Ensure static, media and ML model directories exist with correct permissions
RUN mkdir -p /app/staticfiles /app/mediafiles /app/ai/ml/models /app/ai/ml/data && \
    chown -R memoai:memoai /app/staticfiles /app/mediafiles /app/ai/ml/models /app/ai/ml/data

# Collect static files (Whitenoise will serve them in production)
RUN python manage.py collectstatic --noinput --settings=config.settings || true

USER memoai

EXPOSE $PORT

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/health/ || exit 1

# Start Gunicorn (single container — Render free tier)
CMD ["sh", "-c", "gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --keepalive 5 \
    --log-level warning \
    --access-logfile - \
    --error-logfile -"]
