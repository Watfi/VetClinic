"""Shared helpers for the new ORM-based views."""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from home.models import Usuario


def _get_session(request):
    return request.session.get("user"), request.session.get("rol")


def login_required_custom(view_func):
    """Ensure session has a logged-in user (any role)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        username, _ = _get_session(request)
        if not username:
            messages.warning(request, "Inicia sesión primero.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped


def superadmin_required(view_func):
    """Ensure request belongs to a logged-in SuperAdministrador."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        username, rol = _get_session(request)
        if not username:
            messages.warning(request, "Inicia sesión primero.")
            return redirect("login")
        if rol != Usuario.ROL_SUPERADMIN:
            messages.error(request, "Acceso restringido a superadministradores.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    """Ensure request belongs to a logged-in Administrador or SuperAdministrador."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        username, rol = _get_session(request)
        if not username:
            messages.warning(request, "Inicia sesión primero.")
            return redirect("login")
        if rol not in (Usuario.ROL_ADMIN, Usuario.ROL_SUPERADMIN):
            messages.error(request, "Acceso restringido a administradores.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def has_module(request, modulo):
    """
    Check if the current session user has access to a given module key.
    - SuperAdmin: always True
    - Admin: True if modulo is in their modulos_acceso list
    - Others: False
    """
    username, rol = _get_session(request)
    if not username:
        return False
    if rol == Usuario.ROL_SUPERADMIN:
        return True
    if rol == Usuario.ROL_ADMIN:
        usuario = Usuario.objects.filter(user=username).first()
        if not usuario:
            return False
        return modulo in (usuario.modulos_acceso or [])
    return False


def module_required(modulo):
    """
    Decorator factory: requires the user to be logged in as SuperAdmin,
    or as Admin with the given module in their modulos_acceso list.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            username, rol = _get_session(request)
            if not username:
                messages.warning(request, "Inicia sesión primero.")
                return redirect("login")
            if not has_module(request, modulo):
                messages.error(request, "No tienes acceso a este módulo.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def vet_or_admin_required(view_func):
    """Allow SuperAdministrador, Administrador and Veterinario roles."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        username, rol = _get_session(request)
        if not username:
            messages.warning(request, "Inicia sesión primero.")
            return redirect("login")
        if rol not in (Usuario.ROL_SUPERADMIN, Usuario.ROL_ADMIN, Usuario.ROL_VET):
            messages.error(request, "Acceso restringido a veterinarios y administradores.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def peluquero_or_above(view_func):
    """Allow all authenticated roles (SuperAdmin, Admin with 'citas' module, Vet, Peluquero)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        username, rol = _get_session(request)
        if not username:
            messages.warning(request, "Inicia sesión primero.")
            return redirect("login")
        if rol == Usuario.ROL_ADMIN:
            if not has_module(request, "citas"):
                messages.error(request, "No tienes acceso a este módulo.")
                return redirect("dashboard")
        elif rol not in (Usuario.ROL_SUPERADMIN, Usuario.ROL_VET, Usuario.ROL_PELUQUERO):
            messages.error(request, "Acceso denegado.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped


def current_user(request):
    """Return Usuario instance for active session, or None."""
    username = request.session.get("user")
    if not username:
        return None
    return Usuario.objects.filter(user=username).first()
