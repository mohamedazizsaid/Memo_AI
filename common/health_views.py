"""
MemoAI — Health Check View
Used by Docker HEALTHCHECK, Render, and load balancers.
GET /health/ → 200 OK (JSON) si l'app + DB sont opérationnelles.
"""

import time
from django.http import JsonResponse
from django.db import connection
from django.db.utils import OperationalError


def health_check(request):
    """
    Lightweight health check endpoint.
    Returns 200 if the app is healthy, 503 otherwise.
    """
    start = time.time()

    # DB check
    db_ok = False
    db_error = None
    try:
        connection.ensure_connection()
        db_ok = True
    except OperationalError as e:
        db_error = str(e)

    elapsed_ms = round((time.time() - start) * 1000, 1)

    status = 200 if db_ok else 503
    payload = {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else f"error: {db_error}",
        "response_time_ms": elapsed_ms,
    }

    return JsonResponse(payload, status=status)
