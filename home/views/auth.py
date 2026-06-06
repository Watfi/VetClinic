"""Authentication views — login / logout / edit profile (admin only)."""

import base64

from django.contrib import messages
from django.shortcuts import redirect, render

from home.models import Usuario

from ._helpers import admin_required, current_user


def login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = Usuario.objects.filter(email=email, password=password).first()
        if not user:
            messages.error(request, "Credenciales incorrectas.")
            return redirect("login")

        request.session["user"] = user.user
        request.session["rol"] = user.rol
        request.session["user_profile_picture"] = user.profile_picture or ""
        messages.success(request, f"Bienvenido {user.nombre or user.user}")

        # Redirect by role
        if user.rol == Usuario.ROL_PELUQUERO:
            return redirect("list_citas")
        elif user.rol == Usuario.ROL_VET:
            return redirect("list_pacientes")
        else:
            return redirect("index")

    return render(request, "login.html")


def logout(request):
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("login")


@admin_required
def edit_profile(request):
    user = current_user(request)
    if not user:
        return redirect("login")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password_actual = request.POST.get("password_actual", "").strip()
        password_nueva = request.POST.get("password_nueva", "").strip()
        password_confirmar = request.POST.get("password_confirmar", "").strip()
        remove_picture = request.POST.get("remove_profile_picture", "") == "true"

        if not email:
            messages.error(request, "Email is required.")
            return redirect("edit_profile")

        if Usuario.objects.filter(email=email).exclude(pk=user.pk).exists():
            messages.error(request, "This email is already in use by another user.")
            return redirect("edit_profile")

        user.email = email

        if remove_picture:
            user.profile_picture = None
        elif "profile_picture" in request.FILES:
            picture = request.FILES["profile_picture"]
            allowed = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
            if picture.content_type not in allowed:
                messages.error(request, "Invalid file type.")
                return redirect("edit_profile")
            if picture.size > 5 * 1024 * 1024:
                messages.error(request, "File size must be less than 5MB.")
                return redirect("edit_profile")
            data_uri = (
                f"data:{picture.content_type};base64,"
                f"{base64.b64encode(picture.read()).decode('utf-8')}"
            )
            user.profile_picture = data_uri

        if password_nueva:
            if password_actual != user.password:
                messages.error(request, "Current password is incorrect.")
                return redirect("edit_profile")
            if password_nueva != password_confirmar:
                messages.error(request, "New passwords do not match.")
                return redirect("edit_profile")
            if len(password_nueva) < 6:
                messages.error(request, "Password must be at least 6 characters long.")
                return redirect("edit_profile")
            user.password = password_nueva

        user.save()
        request.session["user_profile_picture"] = user.profile_picture or ""
        request.session.modified = True
        messages.success(request, "Profile updated successfully!")
        return redirect("edit_profile")

    return render(request, "edit_profile.html", {
        "username": user.user,
        "rol": user.rol,
        "user": {
            "User": user.user,
            "Email": user.email,
            "Rol": user.rol,
            "Phone": user.phone,
            "Address": user.address,
            "profile_picture": user.profile_picture,
        },
        "vet_data": None,
    })
