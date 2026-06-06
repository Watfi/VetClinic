"""Historia clinica CRUD — admin only, ORM."""

import io
import os
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from home.models import HistoriaClinica, Paciente, AdjuntoArchivo

from ._helpers import admin_required, vet_or_admin_required, current_user


_HISTORIA_FIELDS = [
    "hc_numero", "hora",
    "motivo_consulta",
    "subjetivo", "objetivo", "interpretacion", "plan_terapeutico", "plan_diagnostico",
    "anamnesis_dieta", "anamnesis_enfermedades_previas", "anamnesis_esterilizado",
    "anamnesis_num_partos", "anamnesis_cirugias_previas",
    "examen_fisico", "examen_fisico_general", "examen_fisico_especial",
    "diagnostico", "tratamiento", "observaciones",
]


def _mascota_choices():
    out = []
    for m in Paciente.objects.select_related("owner"):
        owner_name = (m.owner.nombre or m.owner.user) if m.owner else "Unknown"
        out.append({
            "id": m.id,
            "id_str": str(m.id),
            "_id": m.id,
            "nombre": m.nombre,
            "especie": m.especie,
            "owner_name": owner_name,
            "display_name": f"{m.nombre} ({m.especie}) - Owner: {owner_name}",
        })
    return out


def _paciente_card(m):
    if not m:
        return {}
    owner = m.owner
    return {
        "id_str": str(m.id),
        "nombre": m.nombre,
        "especie": m.especie,
        "raza": m.raza,
        "profile_picture": m.profile_picture,
        "owner_nombre": (owner.nombre or owner.user) if owner else "",
        "owner_email": m.owner_email or (owner.email if owner else ""),
        "owner_telefono": m.owner_telefono or (owner.phone if owner else ""),
        "owner_direccion": m.owner_direccion or (owner.address if owner else ""),
        "owner_documento": m.owner_documento,
        "owner_tipo_documento": m.owner_tipo_documento,
    }


def _historia_to_legacy(h):
    data = {
        "id": h.id,
        "id_str": str(h.id),
        "_id": h.id,
        "id_paciente": h.paciente_id,
        "fecha": h.fecha.strftime("%Y-%m-%d") if h.fecha else "",
        "fecha_formatted": h.fecha.strftime("%B %d, %Y") if h.fecha else "",
    }
    for f in _HISTORIA_FIELDS:
        data[f] = getattr(h, f, "")

    if h.paciente_id:
        m = h.paciente
        data["mascota_nombre"] = m.nombre
        data["mascota_especie"] = m.especie
        data["mascota_raza"] = m.raza
        card = _paciente_card(m)
        data["mascota"] = card
        data["paciente_card"] = card
        data["propietario_nombre"] = card["owner_nombre"]

    data["puede_editar"] = True
    data["puede_eliminar"] = True
    return data


@vet_or_admin_required
def list_historias(request):
    historias = [_historia_to_legacy(h) for h in HistoriaClinica.objects.select_related("paciente", "paciente__owner")]
    return render(request, "medical_history_list.html", {
        "historias": historias,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
        "total": len(historias),
    })


@vet_or_admin_required
def view_historia(request, id):
    h = HistoriaClinica.objects.select_related("paciente", "paciente__owner").filter(pk=id).first()
    if not h:
        messages.error(request, "Medical history not found.")
        return redirect("list_historias")
    # Determine back URL: prefer coming from historia_paciente tab
    back_url = request.GET.get("back_url") or ""
    if not back_url and h.paciente_id:
        back_url = f"/patients/mascotas/{h.paciente_id}/historia/?tab=consultas"
    if not back_url:
        back_url = "/historias/"
    return render(request, "medical_history_detail.html", {
        "historia": _historia_to_legacy(h),
        "back_url": back_url,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
        "puede_editar": True,
        "puede_eliminar": True,
    })


def _populate_from_post(historia, request, paciente_id):
    for f in _HISTORIA_FIELDS:
        setattr(historia, f, request.POST.get(f) or "")
    historia.paciente_id = paciente_id
    fecha_str = request.POST.get("fecha")
    if fecha_str:
        try:
            historia.fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    proximo_str = request.POST.get("proximo_control")
    if proximo_str:
        try:
            historia.proximo_control = datetime.strptime(proximo_str, "%Y-%m-%d").date()
        except ValueError:
            historia.proximo_control = None
    else:
        historia.proximo_control = None


@vet_or_admin_required
def add_historia(request):
    mascotas = _mascota_choices()
    paciente_presel = request.GET.get("paciente", "")

    if request.method == "POST":
        id_paciente = request.POST.get("id_paciente")
        fecha = request.POST.get("fecha")

        if not all([id_paciente, fecha]):
            messages.error(request, "Por favor selecciona un paciente y una fecha.")
            return render(request, "medical_history_form.html", {
                "mascotas": mascotas,
                "action": "Add",
                "paciente_presel": paciente_presel,
                "rol": request.session.get("rol"),
            })

        h = HistoriaClinica(creado_por=current_user(request))
        _populate_from_post(h, request, id_paciente)
        h.save()
        # Guardar adjuntos múltiples
        for f in request.FILES.getlist("adjuntos[]"):
            if f:
                AdjuntoArchivo.objects.create(
                    tipo="consulta", object_id=h.id,
                    archivo=f, nombre_original=f.name,
                )
        messages.success(request, "Consulta registrada correctamente.")
        # Si vino de la historia del paciente, volver ahí
        if id_paciente:
            return redirect(f"/patients/mascotas/{id_paciente}/historia/?tab=consultas")
        return redirect("list_historias")

    return render(request, "medical_history_form.html", {
        "mascotas": mascotas,
        "action": "Add",
        "paciente_presel": paciente_presel,
        "rol": request.session.get("rol"),
    })


@vet_or_admin_required
def edit_historia(request, id):
    h = HistoriaClinica.objects.select_related("paciente", "paciente__owner").filter(pk=id).first()
    if not h:
        messages.error(request, "Medical history not found.")
        return redirect("list_historias")

    mascotas = _mascota_choices()

    if request.method == "POST":
        id_paciente = request.POST.get("id_paciente")
        fecha = request.POST.get("fecha")

        if not all([id_paciente, fecha]):
            messages.error(request, "Please select a patient and a date.")
            return render(request, "medical_history_form.html", {
                "historia": _historia_to_legacy(h),
                "mascotas": mascotas,
                "action": "Edit",
                "rol": request.session.get("rol"),
            })

        _populate_from_post(h, request, id_paciente)
        h.save()
        # Guardar adjuntos adicionales
        for f in request.FILES.getlist("adjuntos[]"):
            if f:
                AdjuntoArchivo.objects.create(
                    tipo="consulta", object_id=h.id,
                    archivo=f, nombre_original=f.name,
                )
        messages.success(request, "Consulta actualizada correctamente.")
        next_url = request.POST.get("next_url") or ""
        if next_url:
            return redirect(next_url)
        if id_paciente:
            return redirect(f"/patients/mascotas/{id_paciente}/historia/?tab=consultas")
        return redirect("view_historia", id=id)

    return render(request, "medical_history_form.html", {
        "historia": _historia_to_legacy(h),
        "mascotas": mascotas,
        "action": "Edit",
        "rol": request.session.get("rol"),
    })


@vet_or_admin_required
def consulta_pdf(request, id):
    """PDF individual de una consulta con adjuntos embebidos."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )

    h = HistoriaClinica.objects.select_related("paciente", "paciente__propietario").filter(pk=id).first()
    if not h:
        messages.error(request, "Consulta no encontrada.")
        return redirect("list_historias")

    paciente = h.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Normal"], fontSize=13, fontName="Helvetica-Bold")
    sub_s   = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#444"))
    label_s = ParagraphStyle("L", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#556B2F"))
    value_s = ParagraphStyle("V", parent=styles["Normal"], fontSize=9)
    head_s  = ParagraphStyle("H", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#2d4a1e"))
    body_s  = ParagraphStyle("B", parent=styles["Normal"], fontSize=9, leading=13)

    story = []

    # ── Encabezado ──
    biz_name    = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit     = getattr(settings, "BUSINESS_NIT", "")
    biz_phone   = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")

    logo_path = next((p for p in [
        os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"),
        os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg"),
    ] if os.path.exists(p)), "")
    logo_cell = ""
    if logo_path:
        try: logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception: pass

    biz_lines = f"<b>{biz_name}</b>"
    if biz_nit:     biz_lines += f"<br/>NIT: {biz_nit}"
    if biz_phone:   biz_lines += f"<br/>Tel: {biz_phone}"
    if biz_address: biz_lines += f"<br/>{biz_address}"

    fecha_str = h.fecha.strftime("%d/%m/%Y") if h.fecha else ""
    hdr_tbl = Table([[logo_cell, Paragraph(biz_lines, title_s),
                      Paragraph(f"<b>CONSULTA MEDICA</b><br/>HC #{h.hc_numero or h.id}<br/>Fecha: {fecha_str}", sub_s)]],
                    colWidths=[3*cm, 9.5*cm, 5.5*cm])
    hdr_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("LINEBELOW", (0,0), (-1,-1), 1, colors.HexColor("#556B2F")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Propietario ──
    prop_data = [[Paragraph("<b>DATOS DEL PROPIETARIO</b>", head_s), "", "", ""],
                 [Paragraph("Propietario:", label_s), Paragraph(propietario.nombre if propietario else "—", value_s),
                  Paragraph("Documento:", label_s), Paragraph(
                      f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—", value_s)],
                 [Paragraph("Telefono:", label_s), Paragraph(propietario.telefono if propietario else "—", value_s),
                  Paragraph("Email:", label_s), Paragraph(propietario.email if propietario else "—", value_s)],
                ]
    pt = Table(prop_data, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    pt.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)), ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f4ea")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.3*cm))

    # ── Paciente ──
    if paciente:
        pac_data = [[Paragraph("<b>DATOS DEL PACIENTE</b>", head_s), "", "", ""],
                    [Paragraph("Nombre:", label_s), Paragraph(paciente.nombre or "—", value_s),
                     Paragraph("Especie:", label_s), Paragraph(paciente.especie or "—", value_s)],
                    [Paragraph("Raza:", label_s), Paragraph(paciente.raza or "—", value_s),
                     Paragraph("Sexo:", label_s), Paragraph(getattr(paciente, "sexo", "") or "—", value_s)],
                   ]
        pact = Table(pac_data, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
        pact.setStyle(TableStyle([
            ("SPAN", (0,0), (-1,0)), ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f4ea")),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(pact)
        story.append(Spacer(1, 0.3*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#556B2F"), spaceAfter=0.3*cm))

    # ── Contenido clínico ──
    def _field(label, val):
        if val:
            story.append(Paragraph(f"<b>{label}:</b>", label_s))
            story.append(Paragraph(val, body_s))
            story.append(Spacer(1, 0.2*cm))

    # ── Veterinario responsable ──
    vet_resp = getattr(h, 'creado_por', None)
    if vet_resp:
        vet_resp_str = vet_resp.nombre or vet_resp.user
        if vet_resp.especialidad: vet_resp_str += f" — {vet_resp.especialidad}"
        if vet_resp.license: vet_resp_str += f" | Lic. Prof.: {vet_resp.license}"
        story.append(Paragraph(f"<b>Veterinario:</b> {vet_resp_str}", value_s))
        story.append(Spacer(1, 0.15*cm))

    if h.motivo_consulta:
        story.append(Paragraph(f"<b>Motivo:</b> {h.motivo_consulta}", value_s))
        story.append(Spacer(1, 0.2*cm))

    _field("S — Subjetivo", h.subjetivo)
    _field("O — Objetivo", h.objetivo)
    _field("I — Interpretacion / Dx presuntivo", h.interpretacion)
    _field("P — Plan terapeutico", h.plan_terapeutico)
    _field("P — Plan diagnostico", h.plan_diagnostico)
    _field("Diagnostico", h.diagnostico)
    _field("Tratamiento", h.tratamiento)
    _field("Observaciones", h.observaciones)

    # ── Adjuntos embebidos ──
    all_adj_paths = []
    adj_qs = AdjuntoArchivo.objects.filter(tipo="consulta", object_id=h.id)
    for adj in adj_qs:
        try:
            p = adj.archivo.path
            if os.path.exists(p): all_adj_paths.append(p)
        except Exception: pass

    if all_adj_paths:
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=0.3, color=colors.grey, spaceAfter=0.2*cm))
        story.append(Paragraph("<b>Archivos adjuntos</b>", head_s))
        story.append(Spacer(1, 0.2*cm))
        for ap in all_adj_paths:
            ext = os.path.splitext(ap)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif"):
                try:
                    story.append(RLImage(ap, width=14*cm, height=10*cm, kind="proportional"))
                    story.append(Spacer(1, 0.2*cm))
                except Exception:
                    story.append(Paragraph(f"[Imagen: {os.path.basename(ap)}]", value_s))
            else:
                story.append(Paragraph(f"Adjunto: {os.path.basename(ap)}", value_s))

    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe = f"Consulta_{h.id}.pdf"
    resp["Content-Disposition"] = f'inline; filename="{safe}"'
    return resp


@vet_or_admin_required
def delete_historia(request, id):
    h = HistoriaClinica.objects.filter(pk=id).first()
    if not h:
        messages.error(request, "Medical history not found.")
        return redirect("list_historias")
    h.delete()
    messages.success(request, "Medical history deleted successfully.")
    return redirect("list_historias")
