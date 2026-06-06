"""Recetario module — prescripciones."""

import io
import json
import os
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
try:
    from reportlab.platypus import Image as RLImage
except ImportError:
    RLImage = None

from home.models import Paciente, Receta, RecetaItem, Usuario

from ._helpers import admin_required, vet_or_admin_required, current_user


def _next_numero():
    last = Receta.objects.order_by("-id").first()
    n = (last.id + 1) if last else 1
    return f"RX-{datetime.now().strftime('%Y%m%d')}-{n:05d}"


@vet_or_admin_required
def list_recetas(request):
    recetas = Receta.objects.select_related("paciente", "veterinario").all()
    return render(request, "recetas_list.html", {
        "recetas": recetas,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@vet_or_admin_required
def add_receta(request):
    pacientes = Paciente.objects.select_related("owner").all()
    veterinarios = Usuario.objects.filter(rol=Usuario.ROL_VET)

    if request.method == "POST":
        paciente_id = request.POST.get("paciente")
        if not paciente_id:
            messages.error(request, "Selecciona un paciente.")
            return redirect("add_receta")
        items_json = request.POST.get("items_json") or "[]"
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []
        if not items:
            messages.error(request, "Agrega al menos un medicamento.")
            return redirect("add_receta")

        vet_id = request.POST.get("veterinario") or None

        with transaction.atomic():
            receta = Receta.objects.create(
                numero=_next_numero(),
                paciente_id=int(paciente_id),
                veterinario_id=int(vet_id) if vet_id else None,
                diagnostico=(request.POST.get("diagnostico") or "").strip(),
                indicaciones=(request.POST.get("indicaciones") or "").strip(),
                vigencia_dias=int(request.POST.get("vigencia_dias") or 30),
                creado_por=current_user(request),
            )
            for it in items:
                med = (it.get("medicamento") or "").strip()
                if not med:
                    continue
                RecetaItem.objects.create(
                    receta=receta,
                    medicamento=med,
                    dosis=(it.get("dosis") or "").strip(),
                    via=(it.get("via") or "").strip(),
                    frecuencia=(it.get("frecuencia") or "").strip(),
                    duracion=(it.get("duracion") or "").strip(),
                    observaciones=(it.get("observaciones") or "").strip(),
                )
        messages.success(request, f"Receta {receta.numero} creada.")
        return redirect("view_receta", id=receta.id)

    return render(request, "recetas_form.html", {
        "pacientes": pacientes,
        "veterinarios": veterinarios,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@vet_or_admin_required
def view_receta(request, id):
    receta = get_object_or_404(
        Receta.objects.select_related("paciente", "veterinario").prefetch_related("items"),
        pk=int(id),
    )
    back_url = request.GET.get("back_url") or ""
    if not back_url and receta.paciente_id:
        back_url = f"/patients/mascotas/{receta.paciente_id}/historia/?tab=recetas"
    if not back_url:
        back_url = "/recetas/"
    return render(request, "recetas_detail.html", {
        "receta": receta,
        "back_url": back_url,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@vet_or_admin_required
def delete_receta(request, id):
    receta = get_object_or_404(Receta, pk=int(id))
    receta.delete()
    messages.success(request, "Receta eliminada.")
    return redirect("list_recetas")


@vet_or_admin_required
def receta_pdf(request, id):
    receta = get_object_or_404(
        Receta.objects.select_related("paciente", "paciente__propietario", "veterinario").prefetch_related("items"),
        pk=int(id),
    )
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_s  = ParagraphStyle("TitleS",  parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold", spaceAfter=2)
    sub_s    = ParagraphStyle("SubS",    parent=styles["Normal"], fontSize=9,  textColor=colors.HexColor("#444444"))
    label_s  = ParagraphStyle("LabelS",  parent=styles["Normal"], fontSize=8,  fontName="Helvetica-Bold", textColor=colors.HexColor("#556B2F"))
    value_s  = ParagraphStyle("ValueS",  parent=styles["Normal"], fontSize=9)
    head_s   = ParagraphStyle("HeadS",   parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#2d4a1e"))

    story = []

    # ── Encabezado ──────────────────────────────────────────────────────────
    biz_name    = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit     = getattr(settings, "BUSINESS_NIT", "")
    biz_phone   = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")

    logo_path = next((p for p in [
        os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"),
        os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg"),
    ] if os.path.exists(p)), "")
    logo_cell = ""
    if RLImage and logo_path:
        try:
            logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception:
            logo_cell = ""

    biz_lines = f"<b>{biz_name}</b>"
    if biz_nit:     biz_lines += f"<br/>NIT: {biz_nit}"
    if biz_phone:   biz_lines += f"<br/>Tel: {biz_phone}"
    if biz_address: biz_lines += f"<br/>{biz_address}"

    fecha_receta = timezone.localtime(receta.fecha).strftime("%d/%m/%Y %H:%M") if receta.fecha else ""

    header_tbl = Table(
        [[logo_cell, Paragraph(biz_lines, title_s),
          Paragraph(f"<b>FÓRMULA MÉDICA</b><br/>{receta.numero}<br/>Fecha: {fecha_receta}", sub_s)]],
        colWidths=[3*cm, 9.5*cm, 5.5*cm],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#556B2F")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Propietario ──────────────────────────────────────────────────────────
    paciente = receta.paciente
    prop = paciente.propietario if paciente else None
    owner_nombre   = prop.nombre if prop else ""
    owner_email    = prop.email if prop else ""
    owner_telefono = prop.telefono if prop else ""
    owner_direccion= prop.direccion if prop else ""
    owner_doc      = f"{prop.tipo_documento}: {prop.numero_documento}" if prop and prop.numero_documento else ""

    prop_data = [
        [Paragraph("<b>DATOS DEL PROPIETARIO</b>", head_s), "", "", ""],
        [Paragraph("Propietario:", label_s), Paragraph(owner_nombre or "—", value_s),
         Paragraph("Documento:", label_s),   Paragraph(owner_doc or "—", value_s)],
        [Paragraph("Email:", label_s),       Paragraph(owner_email or "—", value_s),
         Paragraph("Teléfono:", label_s),    Paragraph(owner_telefono or "—", value_s)],
        [Paragraph("Dirección:", label_s),   Paragraph(owner_direccion or "—", value_s), "", ""],
    ]
    prop_tbl = Table(prop_data, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    prop_tbl.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("SPAN", (1, 3), (-1, 3)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ea")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(prop_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Paciente ──────────────────────────────────────────────────────────
    if paciente:
        pac_data = [
            [Paragraph("<b>DATOS DEL PACIENTE</b>", head_s), "", "", ""],
            [Paragraph("Nombre:", label_s),  Paragraph(paciente.nombre or "—", value_s),
             Paragraph("Especie:", label_s), Paragraph(paciente.especie or "—", value_s)],
            [Paragraph("Raza:", label_s),    Paragraph(paciente.raza or "—", value_s),
             Paragraph("Sexo:", label_s),    Paragraph(getattr(paciente, "sexo", "") or "—", value_s)],
        ]
        pac_tbl = Table(pac_data, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
        pac_tbl.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ea")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(pac_tbl)
        story.append(Spacer(1, 0.3*cm))

    # ── Veterinario / Diagnóstico ─────────────────────────────────────────
    if receta.veterinario:
        vet = receta.veterinario
        vet_name = vet.nombre or vet.user
        vet_lic  = getattr(vet, "license", "") or ""
        story.append(Paragraph(f"<b>Veterinario:</b> {vet_name}"
                               + (f" · Lic. {vet_lic}" if vet_lic else ""), value_s))
    if receta.diagnostico:
        story.append(Paragraph(f"<b>Diagnóstico:</b> {receta.diagnostico}", value_s))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#556B2F"), spaceAfter=0.3*cm))

    # ── Medicamentos ──────────────────────────────────────────────────────
    story.append(Paragraph("<b>MEDICAMENTOS PRESCRITOS</b>", head_s))
    story.append(Spacer(1, 0.2*cm))

    med_data = [["#", "Medicamento", "Presentación", "Cantidad", "Posología"]]
    for idx, it in enumerate(receta.items.all(), 1):
        med_data.append([
            str(idx),
            it.medicamento or "—",
            it.presentacion or "—",
            str(it.cantidad or "1"),
            it.posologia or "—",
        ])
    med_tbl = Table(med_data, colWidths=[0.8*cm, 5.5*cm, 3.5*cm, 2*cm, 6.2*cm])
    med_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#556B2F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(med_tbl)

    if receta.indicaciones:
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(f"<b>Indicaciones generales:</b>", label_s))
        story.append(Paragraph(receta.indicaciones, value_s))

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black,
                            spaceAfter=0.1*cm, hAlign="LEFT"))
    if receta.veterinario:
        vet = receta.veterinario
        story.append(Paragraph(f"<b>{vet.nombre or vet.user}</b>", value_s))
        lic = getattr(vet, "license", "") or ""
        if lic:
            story.append(Paragraph(f"Lic. {lic}", ParagraphStyle("sm", parent=styles["Normal"], fontSize=8, textColor=colors.grey)))
    story.append(Paragraph("Médico Veterinario responsable", ParagraphStyle("sm2", parent=styles["Normal"], fontSize=8, textColor=colors.grey)))

    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{receta.numero}.pdf"'
    return resp
