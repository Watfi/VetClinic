"""Módulo de gestión de tarifas de citas."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import redirect, render

from home.models import TarifaCita
from ._helpers import admin_required


def _ensure_default_tarifas():
    """Create default tarifa entries if they don't exist yet."""
    for tipo, precio in TarifaCita.DEFAULT_TIPOS:
        TarifaCita.objects.get_or_create(
            tipo=tipo,
            defaults={"precio": precio, "activo": True},
        )


@admin_required
def list_tarifas(request):
    _ensure_default_tarifas()
    tarifas = list(TarifaCita.objects.all())
    return render(request, "tarifas_list.html", {
        "tarifas": tarifas,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@admin_required
def add_tarifa(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo", "").strip()
        precio_str = request.POST.get("precio", "0").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        activo = request.POST.get("activo") == "on"

        if not tipo:
            messages.error(request, "El tipo de cita es obligatorio.")
            return redirect("list_tarifas")
        try:
            precio = Decimal(precio_str)
        except (InvalidOperation, ValueError):
            precio = Decimal("0")

        if TarifaCita.objects.filter(tipo=tipo).exists():
            messages.error(request, f"Ya existe una tarifa para «{tipo}».")
            return redirect("list_tarifas")

        categoria = request.POST.get("categoria", "Medica")
        if categoria not in ("Medica", "Peluqueria"):
            categoria = "Medica"
        TarifaCita.objects.create(tipo=tipo, precio=precio, descripcion=descripcion, activo=activo, categoria=categoria)
        messages.success(request, f"Tarifa «{tipo}» creada correctamente.")
    return redirect("list_tarifas")


@admin_required
def edit_tarifa(request, id):
    t = TarifaCita.objects.filter(pk=id).first()
    if not t:
        messages.error(request, "Tarifa no encontrada.")
        return redirect("list_tarifas")

    if request.method == "POST":
        precio_str = request.POST.get("precio", "0").strip()
        t.descripcion = request.POST.get("descripcion", "").strip()
        t.activo = request.POST.get("activo") == "on"
        categoria = request.POST.get("categoria", t.categoria or "Medica")
        if categoria not in ("Medica", "Peluqueria"):
            categoria = "Medica"
        t.categoria = categoria
        try:
            t.precio = Decimal(precio_str)
        except (InvalidOperation, ValueError):
            t.precio = Decimal("0")
        t.save()
        messages.success(request, f"Tarifa «{t.tipo}» actualizada.")
    return redirect("list_tarifas")


@admin_required
def delete_tarifa(request, id):
    t = TarifaCita.objects.filter(pk=id).first()
    if t:
        nombre = t.tipo
        t.delete()
        messages.info(request, f"Tarifa «{nombre}» eliminada.")
    return redirect("list_tarifas")
