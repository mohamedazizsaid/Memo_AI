"""
MemoAi — Common Permissions
Custom DRF permission classes for user isolation.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwner(BasePermission):
    """
    Only the owner of the object can access it.
    Object must have a 'user' field.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwnerOrReadOnly(BasePermission):
    """Allow read for authenticated users, write only for owner."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return obj.user == request.user


class IsSelf(BasePermission):
    """User can only access their own user record."""
    message = "You can only access your own account."

    def has_object_permission(self, request, view, obj):
        return obj == request.user
