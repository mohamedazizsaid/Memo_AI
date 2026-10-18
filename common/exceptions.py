"""
MemoAi — Custom Exception Handler
Provides consistent error responses across all API endpoints.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('memoai')


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns a consistent error format:
    {
        "success": false,
        "error": {
            "code": "error_code",
            "message": "Human readable message",
            "details": {}  // Optional additional details
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'success': False,
            'error': {
                'code': _get_error_code(response.status_code),
                'message': _extract_message(response.data),
                'details': response.data if isinstance(response.data, dict) else {},
            }
        }
        response.data = error_data

    return response


def _get_error_code(status_code):
    codes = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        408: 'request_timeout',
        409: 'conflict',
        422: 'unprocessable_entity',
        429: 'rate_limit_exceeded',
        500: 'internal_server_error',
        502: 'bad_gateway',
        503: 'service_unavailable',
    }
    return codes.get(status_code, 'unknown_error')


def _extract_message(data):
    if isinstance(data, dict):
        if 'detail' in data:
            detail = data['detail']
            if hasattr(detail, 'string'):
                return str(detail)
            return str(detail)
        if 'non_field_errors' in data:
            errors = data['non_field_errors']
            if isinstance(errors, list) and errors:
                return str(errors[0])
        # Return first field error
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            elif isinstance(value, str):
                return f"{key}: {value}"
    elif isinstance(data, list) and data:
        return str(data[0])
    return str(data)


class ServiceUnavailableError(Exception):
    """Raised when an external service (AI, Cloudinary) is unavailable."""
    pass


class ValidationError(Exception):
    """Raised when validation fails in a service layer."""
    pass


class QuotaExceededError(Exception):
    """Raised when an API quota is exceeded."""
    pass
