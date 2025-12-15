# users/permissions.py

from rest_framework import permissions

class IsPatient(permissions.BasePermission):
    """Autorise uniquement l'accès si l'utilisateur est un patient."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.userRole == 'Patient'

class IsDoctor(permissions.BasePermission):
    """Autorise uniquement l'accès si l'utilisateur est un médecin."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.userRole == 'Médecin'

class IsLabo(permissions.BasePermission):
    """Autorise uniquement l'accès si l'utilisateur est un laboratoire."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.userRole == 'Laboratoire'