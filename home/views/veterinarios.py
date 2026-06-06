"""Veterinarios CRUD — admin only, ORM.

Veterinarios son ``Usuario`` con ``rol == ROL_VET``. No se les permite iniciar
sesión en la app de escritorio (sólo admin), pero se mantienen como entidades
con sus datos para citas, historias y reportes.
"""

import base64

from django.contrib import messages
from django.shortcuts import redirect, render

from home.models import Usuario

from ._helpers import admin_required


_ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _to_legacy(v):
    return {
        "id": v.id,
        "_id": v.id,
        "User": v.user,
        "Email": v.email,
        "nombre": v.nombre,
        "especialidad": v.especialidad,
        "phone": v.phone,
        "license": v.license,
        "profile_picture": v.profile_picture,
        "Rol": v.rol,
        "ofrece_consulta_medica": v.ofrece_consulta_medica,
        "ofrece_peluqueria": v.ofrece_peluqueria,
    }


def _decode_picture(request):
    if "profile_picture" not in request.FILES:
        return None, None
    pic = request.FILES["profile_picture"]
    if pic.size == 0:
        return None, "The uploaded file is empty."
    if pic.content_type not in _ALLOWED_IMAGE_TYPES:
        return None, "Invalid file type."
    if pic.size > _MAX_IMAGE_BYTES:
        return None, "File size must be less than 5MB."
    encoded = base64.b64encode(pic.read()).decode("utf-8")
    return f"data:{pic.content_type};base64,{encoded}", None


@admin_required
def list_veterinarios(request):
    data = [_to_legacy(v) for v in Usuario.objects.filter(rol=Usuario.ROL_VET)]
    return render(request, "vets_list.html", {
        "vets": data,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@admin_required
def add_veterinario(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        nombre = request.POST.get("nombre", "").strip()
        especialidad = request.POST.get("especialidad", "").strip()
        phone = request.POST.get("phone", "").strip()
        license_ = request.POST.get("license", "").strip()

        if not all([username, email, password, nombre, especialidad]):
            messages.error(request, "Username, email, password, name and specialty are required.")
            return redirect("add_veterinario")
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect("add_veterinario")
        if Usuario.objects.filter(user=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("add_veterinario")
        if Usuario.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
            return redirect("add_veterinario")
        if license_ and Usuario.objects.filter(license=license_).exists():
            messages.error(request, "A veterinarian with this license already exists.")
            return redirect("add_veterinario")

        picture, err = _decode_picture(request)
        if err:
            messages.error(request, err)
            return redirect("add_veterinario")

        ofrece_medica = request.POST.get("ofrece_consulta_medica") == "on"
        ofrece_pelo = request.POST.get("ofrece_peluqueria") == "on"

        Usuario.objects.create(
            user=username,
            email=email,
            password=password,
            rol=Usuario.ROL_VET,
            nombre=nombre,
            especialidad=especialidad,
            phone=phone,
            license=license_,
            profile_picture=picture,
            ofrece_consulta_medica=ofrece_medica,
            ofrece_peluqueria=ofrece_pelo,
        )
        messages.success(request, f"Dr. {nombre} added successfully.")
        return redirect("list_veterinarios")

    return render(request, "vets_form.html", {
        "action": "Add",
        "vet": {},
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@admin_required
def edit_veterinario(request, id):
    vet = Usuario.objects.filter(pk=id, rol=Usuario.ROL_VET).first()
    if not vet:
        messages.error(request, "Veterinarian not found.")
        return redirect("list_veterinarios")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password_nueva = request.POST.get("password", "").strip()
        nombre = request.POST.get("nombre", "").strip()
        especialidad = request.POST.get("especialidad", "").strip()
        phone = request.POST.get("phone", "").strip()
        license_ = request.POST.get("license", "").strip()
        remove_picture = request.POST.get("remove_profile_picture", "") == "true"

        ctx = {
            "action": "Edit",
            "vet": _to_legacy(vet),
            "rol": request.session.get("rol"),
            "username": request.session.get("user"),
        }

        if not all([username, email, nombre, especialidad]):
            messages.error(request, "Username, email, name and specialty are required.")
            return render(request, "vets_form.html", ctx)
        if Usuario.objects.filter(user=username).exclude(pk=vet.pk).exists():
            messages.error(request, "Username already exists.")
            return render(request, "vets_form.html", ctx)
        if Usuario.objects.filter(email=email).exclude(pk=vet.pk).exists():
            messages.error(request, "Email already in use.")
            return render(request, "vets_form.html", ctx)
        if license_ and Usuario.objects.filter(license=license_).exclude(pk=vet.pk).exists():
            messages.error(request, "Another veterinarian already has this license.")
            return render(request, "vets_form.html", ctx)
        if password_nueva and len(password_nueva) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, "vets_form.html", ctx)

        vet.user = username
        vet.email = email
        vet.nombre = nombre
        vet.especialidad = especialidad
        vet.phone = phone
        vet.license = license_
        vet.ofrece_consulta_medica = request.POST.get("ofrece_consulta_medica") == "on"
        vet.ofrece_peluqueria = request.POST.get("ofrece_peluqueria") == "on"
        if password_nueva:
            vet.password = password_nueva

        if remove_picture:
            vet.profile_picture = None
        else:
            picture, err = _decode_picture(request)
            if err:
                messages.error(request, err)
                return render(request, "vets_form.html", ctx)
            if picture:
                vet.profile_picture = picture

        vet.save()
        messages.success(request, f"Dr. {nombre} updated successfully.")
        return redirect("list_veterinarios")

    return render(request, "vets_form.html", {
        "action": "Edit",
        "vet": _to_legacy(vet),
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@admin_required
def delete_veterinario(request, id):
    vet = Usuario.objects.filter(pk=id, rol=Usuario.ROL_VET).first()
    if not vet:
        messages.error(request, "Veterinarian not found.")
        return redirect("list_veterinarios")
    nombre = vet.nombre or vet.user
    vet.delete()
    messages.info(request, f"Dr. {nombre} has been deleted.")
    return redirect("list_veterinarios")
