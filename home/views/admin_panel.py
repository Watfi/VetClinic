"""Admin panel — user management. Admin-only ORM."""

from django.contrib import messages
from django.shortcuts import redirect, render

from home.models import Usuario

from ._helpers import admin_required, current_user


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
    }


@admin_required
def admin_users_list(request):
    usuarios = [_usuario_to_legacy(u) for u in Usuario.objects.all()]
    return render(request, "admin_users_list.html", {
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
        "usuarios": usuarios,
        "total_usuarios": len(usuarios),
        "total_admins": sum(1 for u in usuarios if u["Rol"] == Usuario.ROL_ADMIN),
        "total_vets": sum(1 for u in usuarios if u["Rol"] == Usuario.ROL_VET),
        "total_clients": sum(1 for u in usuarios if u["Rol"] == Usuario.ROL_PELUQUERO),
    })


@admin_required
def admin_users_add(request):
    if request.method == "POST":
        user_field = (request.POST.get("user") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        phone = request.POST.get("phone", "")
        address = request.POST.get("address", "")
        rol = request.POST.get("rol") or Usuario.ROL_VET

        if not all([user_field, email, password]):
            messages.error(request, "Username, email and password are required.")
            return redirect("admin_users_add")
        if Usuario.objects.filter(user=user_field).exists():
            messages.error(request, "A user with that username already exists.")
            return redirect("admin_users_add")
        if Usuario.objects.filter(email=email).exists():
            messages.error(request, "A user with that email already exists.")
            return redirect("admin_users_add")

        Usuario.objects.create(
            user=user_field, email=email, password=password,
            phone=phone, address=address, rol=rol,
        )
        messages.success(request, f"User '{user_field}' created successfully.")
        return redirect("admin_users_list")

    return render(request, "admin_users_form.html", {"action": "Add"})


@admin_required
def admin_users_edit(request, id):
    usuario = Usuario.objects.filter(pk=id).first()
    if not usuario:
        messages.error(request, "User not found.")
        return redirect("admin_users_list")

    if request.method == "POST":
        user_field = (request.POST.get("user") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = request.POST.get("phone", "")
        address = request.POST.get("address", "")
        rol = request.POST.get("rol") or usuario.rol

        if Usuario.objects.filter(user=user_field).exclude(pk=usuario.pk).exists():
            messages.error(request, "Another user already has that username.")
            return render(request, "admin_users_form.html", {
                "usuario": _usuario_to_legacy(usuario), "action": "Edit",
            })
        if Usuario.objects.filter(email=email).exclude(pk=usuario.pk).exists():
            messages.error(request, "Another user already has that email.")
            return render(request, "admin_users_form.html", {
                "usuario": _usuario_to_legacy(usuario), "action": "Edit",
            })

        usuario.user = user_field
        usuario.email = email
        usuario.phone = phone
        usuario.address = address
        usuario.rol = rol
        usuario.save()
        messages.success(request, "User updated successfully.")
        return redirect("admin_users_list")

    return render(request, "admin_users_form.html", {
        "usuario": _usuario_to_legacy(usuario), "action": "Edit",
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


@admin_required
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
