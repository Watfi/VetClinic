"""Admin panel — user management.

- SuperAdministrador: full access (create, edit, delete, assign modules)
- Administrador with módulo 'usuarios': can view list and edit other users (no create/delete)
"""

from django.contrib import messages
from django.shortcuts import redirect, render

from home.models import Usuario

from ._helpers import admin_required, superadmin_required, module_required, current_user

MODULOS_LABELS = [
    (Usuario.MODULO_TARIFAS,      "🏷️ Tarifas"),
    (Usuario.MODULO_INVENTARIO,   "📦 Inventario"),
    (Usuario.MODULO_CATEGORIAS,   "🗂️ Categorías"),
    (Usuario.MODULO_VENTAS,       "🛒 Ventas"),
    (Usuario.MODULO_REPORTES,     "📊 Reportes"),
    (Usuario.MODULO_VETERINARIOS, "🩺 Veterinarios"),
    (Usuario.MODULO_USUARIOS,     "👥 Gestionar Usuarios"),
    (Usuario.MODULO_CITAS,        "📅 Citas"),
]


def _usuario_to_legacy(u):
    return {
        "id": u.id,
        "_id": u.id,
        "mongo_id": str(u.id),
        "User": u.user,
        "Email": u.email,
        "Phone": u.phone,
        "Address": u.address,
        "Rol": u.rol,
        "nombre": u.nombre,
        "especialidad": u.especialidad,
        "license": u.license,
        "ofrece_consulta_medica": u.ofrece_consulta_medica,
        "ofrece_peluqueria": u.ofrece_peluqueria,
        "modulos_acceso": u.modulos_acceso or [],
    }


@admin_required
def admin_users_list(request):
    usuarios = [_usuario_to_legacy(u) for u in Usuario.objects.all()]
    return render(request, "admin_users_list.html", {
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
        "usuarios": usuarios,
        "total_usuarios": len(usuarios),
        "total_superadmins": sum(1 for u in usuarios if u["Rol"] == Usuario.ROL_SUPERADMIN),
        "total_admins": sum(1 for u in usuarios if u["Rol"] in (Usuario.ROL_ADMIN, Usuario.ROL_SUPERADMIN)),
        "total_vets": sum(1 for u in usuarios if u["Rol"] == Usuario.ROL_VET or u["ofrece_consulta_medica"] or u["ofrece_peluqueria"]),
        "total_clients": sum(1 for u in usuarios if u["Rol"] == Usuario.ROL_PELUQUERO),
    })


@superadmin_required
def admin_users_add(request):
    if request.method == "POST":
        user_field = (request.POST.get("user") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        phone = request.POST.get("phone", "")
        address = request.POST.get("address", "")
        rol = request.POST.get("rol") or Usuario.ROL_VET

        # Professional / Clinical fields
        nombre = (request.POST.get("nombre") or "").strip()
        especialidad = (request.POST.get("especialidad") or "").strip()
        license_ = (request.POST.get("license") or "").strip()
        ofrece_consulta_medica = request.POST.get("ofrece_consulta_medica") == "on"
        ofrece_peluqueria = request.POST.get("ofrece_peluqueria") == "on"

        # Module access (only relevant for Admin role)
        modulos_acceso = request.POST.getlist("modulos_acceso")

        if not all([user_field, email, password]):
            messages.error(request, "Username, email and password are required.")
            return render(request, "admin_users_form.html", {
                "action": "Add", "modulos_labels": MODULOS_LABELS,
            })
        if Usuario.objects.filter(user=user_field).exists():
            messages.error(request, "A user with that username already exists.")
            return render(request, "admin_users_form.html", {
                "action": "Add", "modulos_labels": MODULOS_LABELS,
            })
        if Usuario.objects.filter(email=email).exists():
            messages.error(request, "A user with that email already exists.")
            return render(request, "admin_users_form.html", {
                "action": "Add", "modulos_labels": MODULOS_LABELS,
            })

        Usuario.objects.create(
            user=user_field, email=email, password=password,
            phone=phone, address=address, rol=rol,
            nombre=nombre, especialidad=especialidad, license=license_,
            ofrece_consulta_medica=ofrece_consulta_medica,
            ofrece_peluqueria=ofrece_peluqueria,
            modulos_acceso=modulos_acceso if rol == Usuario.ROL_ADMIN else [],
        )
        messages.success(request, f"User '{user_field}' created successfully.")
        return redirect("admin_users_list")

    return render(request, "admin_users_form.html", {
        "action": "Add",
        "modulos_labels": MODULOS_LABELS,
    })


@admin_required
def admin_users_edit(request, id):
    usuario = Usuario.objects.filter(pk=id).first()
    if not usuario:
        messages.error(request, "User not found.")
        return redirect("admin_users_list")

    # Only SuperAdmin can edit other SuperAdmins or change roles freely
    session_rol = request.session.get("rol")
    is_superadmin_session = session_rol == Usuario.ROL_SUPERADMIN

    if request.method == "POST":
        user_field = (request.POST.get("user") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = request.POST.get("phone", "")
        address = request.POST.get("address", "")
        # Only SuperAdmin can change the role
        rol = request.POST.get("rol") if is_superadmin_session else usuario.rol

        # Professional / Clinical fields
        nombre = (request.POST.get("nombre") or "").strip()
        especialidad = (request.POST.get("especialidad") or "").strip()
        license_ = (request.POST.get("license") or "").strip()
        ofrece_consulta_medica = request.POST.get("ofrece_consulta_medica") == "on"
        ofrece_peluqueria = request.POST.get("ofrece_peluqueria") == "on"

        # Module access: only SuperAdmin can change; only relevant for Admin role
        if is_superadmin_session:
            modulos_acceso = request.POST.getlist("modulos_acceso")
        else:
            modulos_acceso = usuario.modulos_acceso or []

        if Usuario.objects.filter(user=user_field).exclude(pk=usuario.pk).exists():
            messages.error(request, "Another user already has that username.")
            return render(request, "admin_users_form.html", {
                "usuario": _usuario_to_legacy(usuario), "action": "Edit",
                "modulos_labels": MODULOS_LABELS, "is_superadmin_session": is_superadmin_session,
            })
        if Usuario.objects.filter(email=email).exclude(pk=usuario.pk).exists():
            messages.error(request, "Another user already has that email.")
            return render(request, "admin_users_form.html", {
                "usuario": _usuario_to_legacy(usuario), "action": "Edit",
                "modulos_labels": MODULOS_LABELS, "is_superadmin_session": is_superadmin_session,
            })

        usuario.user = user_field
        usuario.email = email
        usuario.phone = phone
        usuario.address = address
        usuario.rol = rol or usuario.rol
        usuario.nombre = nombre
        usuario.especialidad = especialidad
        usuario.license = license_
        usuario.ofrece_consulta_medica = ofrece_consulta_medica
        usuario.ofrece_peluqueria = ofrece_peluqueria
        usuario.modulos_acceso = modulos_acceso if usuario.rol == Usuario.ROL_ADMIN else []
        usuario.save()
        messages.success(request, "User updated successfully.")
        return redirect("admin_users_list")

    return render(request, "admin_users_form.html", {
        "usuario": _usuario_to_legacy(usuario),
        "action": "Edit",
        "modulos_labels": MODULOS_LABELS,
        "is_superadmin_session": is_superadmin_session,
    })


@admin_required
def admin_users_reset_password(request, id):
    usuario = Usuario.objects.filter(pk=id).first()
    if not usuario:
        messages.error(request, "User not found.")
        return redirect("admin_users_list")

    if request.method == "POST":
        new_password = request.POST.get("password") or ""
        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect("admin_users_reset_password", id=id)
        usuario.password = new_password
        usuario.save(update_fields=["password"])
        messages.success(request, f"Password for '{usuario.user}' has been reset.")
        return redirect("admin_users_list")

    return render(request, "admin_users_reset.html", {"usuario": _usuario_to_legacy(usuario)})


@superadmin_required
def admin_users_delete(request, id):
    usuario = Usuario.objects.filter(pk=id).first()
    if not usuario:
        messages.error(request, "User not found.")
        return redirect("admin_users_list")

    me = current_user(request)
    if me and me.pk == usuario.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("admin_users_list")

    name = usuario.user
    usuario.delete()
    messages.success(request, f"User '{name}' deleted successfully.")
    return redirect("admin_users_list")
