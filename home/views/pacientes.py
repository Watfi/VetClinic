"""Pacientes (mascotas) CRUD — admin only, ORM."""

import base64

from django.contrib import messages
from django.shortcuts import redirect, render

from home.models import Paciente

from ._helpers import admin_required, vet_or_admin_required


_ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _to_legacy(p):
    return {
        "id": p.id,
        "_id": p.id,
        "nombre": p.nombre,
        "especie": p.especie,
        "raza": p.raza,
        "sexo": p.sexo,
        "profile_picture": p.profile_picture,
        "id_user": p.owner_id,
        "owner_tipo_documento": p.owner_tipo_documento,
        "owner_documento": p.owner_documento,
        "owner_email": p.owner_email,
        "owner_direccion": p.owner_direccion,
        "owner_telefono": p.owner_telefono,
        "owner_nombre": (p.owner.nombre or p.owner.user) if p.owner_id else "",
    }


def _read_owner_fields(request):
    return {
        "owner_tipo_documento": (request.POST.get("owner_tipo_documento") or "").strip(),
        "owner_documento": (request.POST.get("owner_documento") or "").strip(),
        "owner_email": (request.POST.get("owner_email") or "").strip(),
        "owner_direccion": (request.POST.get("owner_direccion") or "").strip(),
        "owner_telefono": (request.POST.get("owner_telefono") or "").strip(),
    }


def _decode_picture(request, redirect_name):
    if "profile_picture" not in request.FILES:
        return None, None
    pic = request.FILES["profile_picture"]
    if pic.size == 0:
        return None, "The uploaded file is empty."
    if pic.content_type not in _ALLOWED_IMAGE_TYPES:
        return None, "Invalid file type. Only JPG, PNG, GIF, and WEBP are allowed."
    if pic.size > _MAX_IMAGE_BYTES:
        return None, "File size must be less than 5MB."
    encoded = base64.b64encode(pic.read()).decode("utf-8")
    return f"data:{pic.content_type};base64,{encoded}", None


@vet_or_admin_required
def list_pacientes(request):
    data = [_to_legacy(p) for p in Paciente.objects.all()]
    return render(request, "patients_list.html", {
        "patients": data,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def add_paciente(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        especie = request.POST.get("especie", "").strip()
        raza = request.POST.get("raza", "").strip()
        sexo = request.POST.get("sexo", "Desconocido").strip()

        if not nombre or not especie or not raza:
            messages.error(request, "Nombre, especie y raza son obligatorios.")
            return redirect("add_paciente")

        picture, err = _decode_picture(request, "add_paciente")
        if err:
            messages.error(request, err)
            return redirect("add_paciente")

        owner_fields = _read_owner_fields(request)
        Paciente.objects.create(
            nombre=nombre,
            especie=especie,
            raza=raza,
            sexo=sexo,
            profile_picture=picture,
            **owner_fields,
        )
        messages.success(request, f"{nombre} added successfully.")
        return redirect("list_pacientes")

    return render(request, "patients_form.html", {
        "action": "Add",
        "paciente": {},
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def edit_paciente(request, id):
    paciente = Paciente.objects.filter(pk=id).first()
    if not paciente:
        messages.error(request, "Pet not found.")
        return redirect("list_pacientes")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        especie = request.POST.get("especie", "").strip()
        raza = request.POST.get("raza", "").strip()
        sexo = request.POST.get("sexo", "Desconocido").strip()
        remove_picture = request.POST.get("remove_profile_picture", "") == "true"

        if not nombre or not especie or not raza:
            messages.error(request, "Nombre, especie y raza son obligatorios.")
            return render(request, "patients_form.html", {
                "action": "Edit",
                "paciente": _to_legacy(paciente),
                "rol": request.session.get("rol"),
                "username": request.session.get("user"),
            })

        paciente.nombre = nombre
        paciente.especie = especie
        paciente.raza = raza
        paciente.sexo = sexo
        for k, v in _read_owner_fields(request).items():
            setattr(paciente, k, v)

        if remove_picture:
            paciente.profile_picture = None
        else:
            picture, err = _decode_picture(request, "edit_paciente")
            if err:
                messages.error(request, err)
                return render(request, "patients_form.html", {
                    "action": "Edit",
                    "paciente": _to_legacy(paciente),
                    "rol": request.session.get("rol"),
                    "username": request.session.get("user"),
                })
            if picture:
                paciente.profile_picture = picture

        paciente.save()
        messages.success(request, f"{nombre}'s information updated successfully.")
        return redirect("list_pacientes")

    return render(request, "patients_form.html", {
        "action": "Edit",
        "paciente": _to_legacy(paciente),
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def delete_paciente(request, id):
    paciente = Paciente.objects.filter(pk=id).first()
    if not paciente:
        messages.error(request, "Pet not found.")
        return redirect("list_pacientes")

    nombre = paciente.nombre
    paciente.delete()
    messages.info(request, f"{nombre} has been removed.")
    return redirect("list_pacientes")
