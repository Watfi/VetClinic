"""Citas (appointments) — admin only, ORM. Single-step booking, no payments."""

from datetime import datetime, time as dt_time, timedelta
from collections import defaultdict
import calendar as _calendar
import io

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from home.models import Cita, Paciente, Propietario, Usuario, TarifaCita

from ._helpers import admin_required, peluquero_or_above, vet_or_admin_required


# --- public read-only API for booking calendar -----------------------------

@peluquero_or_above
def citas_por_mes(request):
    """GET ?year=YYYY&month=MM → JSON {date_iso: [{hora, paciente, vet, estado, tipo}]}"""
    try:
        year = int(request.GET.get("year") or timezone.now().year)
        month = int(request.GET.get("month") or timezone.now().month)
    except (TypeError, ValueError):
        now = timezone.now()
        year, month = now.year, now.month

    # Bounds for the month
    last_day = _calendar.monthrange(year, month)[1]
    start = datetime(year, month, 1)
    end = datetime(year, month, last_day, 23, 59, 59)

    qs = (Cita.objects
          .filter(fecha__gte=start, fecha__lte=end)
          .exclude(estado="Cancelada")
          .select_related("paciente", "veterinario")
          .order_by("fecha"))

    data = defaultdict(list)
    for c in qs:
        key = c.fecha.date().isoformat()
        data[key].append({
            "hora": timezone.localtime(c.fecha).strftime("%H:%M"),
            "paciente": c.paciente.nombre if c.paciente else "—",
            "vet": (c.veterinario.nombre or c.veterinario.user) if c.veterinario else "—",
            "estado": c.estado,
            "tipo": c.tipo or "Cita",
            "duracion": c.duracion or 30,
        })

    return JsonResponse({"year": year, "month": month, "days": data})


# --- background helper -----------------------------------------------------

def _autocomplete_due_appointments():
    """Mark Pendiente appointments as Completada once their end time has passed."""
    now = timezone.now()
    for c in Cita.objects.filter(estado="Pendiente"):
        end = c.fecha_fin or (c.fecha + timedelta(minutes=c.duracion or 30))
        if end <= now:
            c.estado = "Completada"
            c.save(update_fields=["estado"])


# --- form helpers ----------------------------------------------------------

_OFFICE_OPEN = dt_time(8, 0)
_OFFICE_CLOSE = dt_time(19, 0)
_LUNCH_START = dt_time(12, 0)
_LUNCH_END = dt_time(14, 0)


def _validate_business_hours(fecha_dt, request):
    if fecha_dt.weekday() >= 5:
        messages.error(request, "Appointments are only available Monday through Friday.")
        return False
    hora = fecha_dt.time()
    if hora < _OFFICE_OPEN or hora >= _OFFICE_CLOSE:
        messages.error(request, "Appointments must be between 8:00 AM and 7:00 PM.")
        return False
    if _LUNCH_START <= hora < _LUNCH_END:
        messages.error(request, "No appointments during lunch break (12:00 PM – 2:00 PM).")
        return False
    return True


def _conflict(vet_id, fecha_dt, fecha_fin, exclude_id=None):
    """Return a dict describing the conflicting appointment, or ``None``."""
    qs = Cita.objects.filter(
        veterinario_id=vet_id,
        estado__in=["Pendiente", "Completada"],
    )
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    for other in qs:
        other_end = other.fecha_fin or (other.fecha + timedelta(minutes=other.duracion or 30))
        if fecha_dt < other_end and fecha_fin > other.fecha:
            return {
                "inicio": other.fecha.strftime("%I:%M %p"),
                "fin": other_end.strftime("%I:%M %p"),
                "fecha": other.fecha.strftime("%B %d, %Y"),
            }
    return None


def _mascota_options():
    out = []
    for m in Paciente.objects.select_related("propietario"):
        prop = m.propietario
        prop_nombre = prop.nombre if prop else "Sin propietario"
        prop_id = prop.id if prop else None
        out.append({
            "id": m.id,
            "_id": m.id,
            "nombre": m.nombre,
            "especie": m.especie,
            "propietario_id": prop_id,
            "propietario_nombre": prop_nombre,
            "display_name": f"{m.nombre} ({m.especie})",
        })
    return out


def _propietario_options():
    return [
        {
            "id": p.id,
            "nombre": p.nombre or f"Propietario #{p.id}",
            "telefono": p.telefono or "",
            "documento": p.numero_documento or "",
        }
        for p in Propietario.objects.all()
    ]


def _vet_options():
    return [
        {
            "id": v.id,
            "_id": v.id,
            "nombre": v.nombre or v.user,
            "especialidad": v.especialidad,
            "User": v.user,
            "ofrece_consulta_medica": v.ofrece_consulta_medica,
            "ofrece_peluqueria": v.ofrece_peluqueria,
        }
        for v in Usuario.objects.filter(rol__in=[Usuario.ROL_VET, Usuario.ROL_ADMIN])
    ]


def _cita_to_legacy(c, rol):
    fecha_local = timezone.localtime(c.fecha) if c.fecha and timezone.is_aware(c.fecha) else c.fecha
    fecha_fin_local = timezone.localtime(c.fecha_fin) if c.fecha_fin and timezone.is_aware(c.fecha_fin) else c.fecha_fin
    return {
        "id": c.id,
        "id_str": str(c.id),
        "_id": c.id,
        "id_paciente": c.paciente_id,
        "id_veterinario": c.veterinario_id,
        "fecha": fecha_local.strftime("%Y-%m-%d"),
        "hora": fecha_local.strftime("%H:%M"),
        "fecha_original": fecha_local.strftime("%Y-%m-%dT%H:%M"),
        "fecha_fin": fecha_fin_local.strftime("%Y-%m-%dT%H:%M") if fecha_fin_local else "",
        "motivo": c.motivo,
        "estado": c.estado,
        "duracion": c.duracion,
        "observacion": c.observacion,
        "fecha_observacion": (
            c.fecha_observacion.strftime("%B %d, %Y at %I:%M %p")
            if c.fecha_observacion else ""
        ),
        "tipo": c.tipo,
        "mascota_nombre": c.paciente.nombre if c.paciente_id else "Unknown Pet",
        "mascota_especie": c.paciente.especie if c.paciente_id else "Unknown",
        "veterinario_nombre": (
            c.veterinario.nombre or c.veterinario.user
        ) if c.veterinario_id else "Unknown Vet",
        "puede_editar": rol == Usuario.ROL_ADMIN,
        "puede_cancelar": rol == Usuario.ROL_ADMIN and c.estado == "Pendiente",
        "puede_agregar_observacion": False,
    }


# --- views -----------------------------------------------------------------

@peluquero_or_above
def list_citas(request):
    _autocomplete_due_appointments()
    rol = request.session.get("rol")

    qs = Cita.objects.select_related("paciente", "veterinario").order_by("-fecha")
    data = [_cita_to_legacy(c, rol) for c in qs]

    return render(request, "appointments_list.html", {
        "citas": data,
        "rol": rol,
        "username": request.session.get("user"),
        "total_citas": len(data),
        "pendientes": sum(1 for c in data if c["estado"] == "Pendiente"),
        "completadas": sum(1 for c in data if c["estado"] == "Completada"),
        "canceladas": sum(1 for c in data if c["estado"] == "Cancelada"),
    })


@peluquero_or_above
def add_cita(request):
    mascotas = _mascota_options()
    vets = _vet_options()
    rol = request.session.get("rol")

    if not mascotas:
        messages.error(request, "No hay pacientes registrados. Agrega uno primero.")
        return redirect("list_citas")

    if request.method == "POST":
        tipo = request.POST.get("tipo", "Medica")
        id_paciente = request.POST.get("paciente")
        id_veterinario = request.POST.get("veterinario")
        fecha_str = request.POST.get("fecha")
        motivo = (request.POST.get("motivo") or "").strip()
        try:
            duracion = int(request.POST.get("duracion") or 30)
        except ValueError:
            duracion = 30

        ctx = {"mascotas": mascotas, "vets": vets, "action": "Add", "rol": rol, "tipo_sel": tipo}

        if not all([id_paciente, id_veterinario, fecha_str, motivo]):
            messages.error(request, "Please fill all required fields.")
            return render(request, "appointments_form.html", ctx)

        # Validate professional offers the requested service type
        try:
            vet_obj = Usuario.objects.get(pk=id_veterinario)
            if tipo == "Peluqueria" and not vet_obj.ofrece_peluqueria:
                messages.error(request, "The selected professional does not offer grooming services.")
                return render(request, "appointments_form.html", ctx)
            if tipo == "Medica" and not vet_obj.ofrece_consulta_medica:
                messages.error(request, "The selected professional does not offer medical consultations.")
                return render(request, "appointments_form.html", ctx)
        except Usuario.DoesNotExist:
            messages.error(request, "Professional not found.")
            return render(request, "appointments_form.html", ctx)

        try:
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M")
            if timezone.is_naive(fecha_dt):
                fecha_dt = timezone.make_aware(fecha_dt, timezone.get_current_timezone())
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, "appointments_form.html", ctx)

        fecha_fin = fecha_dt + timedelta(minutes=duracion)
        conflict = _conflict(id_veterinario, fecha_dt, fecha_fin)
        if conflict:
            messages.warning(
                request,
                f"Advertencia: Este profesional ya tiene cita de {conflict['inicio']} a "
                f"{conflict['fin']} el {conflict['fecha']}. Se agendó de todas formas.",
            )

        cita = Cita.objects.create(
            tipo=tipo,
            paciente_id=id_paciente,
            veterinario_id=id_veterinario,
            fecha=fecha_dt,
            fecha_fin=fecha_fin,
            motivo=motivo,
            duracion=duracion,
            estado="Pendiente",
        )

        # Send appointment reminder email to owner
        email_sent = _send_appointment_reminder(cita)
        if email_sent:
            messages.success(request, "Appointment successfully scheduled! Reminder email sent to the owner.")
        else:
            messages.success(request, "Appointment scheduled, but reminder email could not be sent (no email on file).")

        return redirect("list_citas")

    import json
    from decimal import Decimal

    mascotas_by_prop = {}
    for m in mascotas:
        pid = str(m["propietario_id"]) if m["propietario_id"] else "0"
        mascotas_by_prop.setdefault(pid, []).append({"id": m["id"], "nombre": m["nombre"], "especie": m["especie"]})

    propietarios = _propietario_options()
    tarifas = list(TarifaCita.objects.filter(activo=True).order_by("categoria", "tipo").values(
        "tipo", "categoria", "precio"
    ))
    # Convert Decimal prices to floats for JSON serialization
    tarifas_serializable = [
        {**t, "precio": float(t["precio"])} for t in tarifas
    ]
    return render(request, "appointments_form.html", {
        "mascotas": mascotas,
        "mascotas_json": json.dumps(mascotas_by_prop),
        "propietarios_json": json.dumps(propietarios, ensure_ascii=False),
        "tarifas_json": json.dumps(tarifas_serializable),
        "vets": vets,
        "action": "Add",
        "rol": rol,
    })


@peluquero_or_above
def edit_cita(request, id):
    cita = Cita.objects.filter(pk=id).first()
    if not cita:
        messages.error(request, "Appointment not found.")
        return redirect("list_citas")

    mascotas = _mascota_options()
    vets = _vet_options()
    rol = request.session.get("rol")

    if request.method == "POST":
        tipo = request.POST.get("tipo", cita.tipo or "Medica")
        id_paciente = request.POST.get("paciente")
        id_veterinario = request.POST.get("veterinario")
        fecha_str = request.POST.get("fecha")
        motivo = (request.POST.get("motivo") or "").strip()
        try:
            duracion = int(request.POST.get("duracion") or cita.duracion or 30)
        except ValueError:
            duracion = cita.duracion or 30
        ctx_data = _cita_to_legacy(cita, rol)
        ctx = {
            "cita": ctx_data,
            "mascotas": mascotas,
            "vets": vets,
            "action": "Edit",
            "rol": rol,
            "username": request.session.get("user"),
            "tipo_sel": tipo,
        }

        if not all([id_paciente, id_veterinario, fecha_str, motivo]):
            messages.error(request, "Please fill all required fields.")
            return render(request, "appointments_form.html", ctx)

        # Validate professional offers the requested service type
        try:
            vet_obj = Usuario.objects.get(pk=id_veterinario)
            if tipo == "Peluqueria" and not vet_obj.ofrece_peluqueria:
                messages.error(request, "The selected professional does not offer grooming services.")
                return render(request, "appointments_form.html", ctx)
            if tipo == "Medica" and not vet_obj.ofrece_consulta_medica:
                messages.error(request, "The selected professional does not offer medical consultations.")
                return render(request, "appointments_form.html", ctx)
        except Usuario.DoesNotExist:
            messages.error(request, "Professional not found.")
            return render(request, "appointments_form.html", ctx)

        try:
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%dT%H:%M")
            if timezone.is_naive(fecha_dt):
                fecha_dt = timezone.make_aware(fecha_dt, timezone.get_current_timezone())
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, "appointments_form.html", ctx)

        fecha_fin = fecha_dt + timedelta(minutes=duracion)
        conflict = _conflict(id_veterinario, fecha_dt, fecha_fin, exclude_id=cita.pk)
        if conflict:
            messages.warning(
                request,
                f"Advertencia: Este profesional ya tiene cita de {conflict['inicio']} a "
                f"{conflict['fin']} el {conflict['fecha']}. Se actualizó de todas formas.",
            )

        cita.tipo = tipo
        cita.paciente_id = id_paciente
        cita.veterinario_id = id_veterinario
        cita.fecha = fecha_dt
        cita.fecha_fin = fecha_fin
        cita.motivo = motivo
        cita.duracion = duracion
        cita.save()
        messages.success(request, "Appointment updated successfully!")
        return redirect("list_citas")

    import json

    mascotas_by_prop = {}
    for m in mascotas:
        pid = str(m["propietario_id"]) if m["propietario_id"] else "0"
        mascotas_by_prop.setdefault(pid, []).append({"id": m["id"], "nombre": m["nombre"], "especie": m["especie"]})

    cita_legacy = _cita_to_legacy(cita, rol)
    # Preselect propietario for edit
    paciente_obj = Paciente.objects.select_related("propietario").filter(pk=cita.paciente_id).first()
    prop_presel = str(paciente_obj.propietario.id) if paciente_obj and paciente_obj.propietario else ""

    propietarios = _propietario_options()
    tarifas = list(TarifaCita.objects.filter(activo=True).order_by("categoria", "tipo").values(
        "tipo", "categoria", "precio"
    ))
    # Convert Decimal prices to floats for JSON serialization
    tarifas_serializable = [
        {**t, "precio": float(t["precio"])} for t in tarifas
    ]
    return render(request, "appointments_form.html", {
        "cita": cita_legacy,
        "mascotas": mascotas,
        "mascotas_json": json.dumps(mascotas_by_prop),
        "propietarios_json": json.dumps(propietarios, ensure_ascii=False),
        "tarifas_json": json.dumps(tarifas_serializable),
        "prop_presel": prop_presel,
        "vets": vets,
        "action": "Edit",
        "rol": rol,
        "tipo_sel": cita.tipo or "Medica",
        "username": request.session.get("user"),
    })


@peluquero_or_above
def cancel_cita(request, id):
    cita = Cita.objects.filter(pk=id).first()
    if not cita:
        messages.error(request, "Appointment not found.")
        return redirect("list_citas")
    if cita.estado != "Pendiente":
        messages.warning(request, f"Cannot cancel an appointment that is already {cita.estado}.")
        return redirect("list_citas")
    cita.estado = "Cancelada"
    cita.save(update_fields=["estado"])
    messages.info(request, "Appointment cancelled successfully.")
    return redirect("list_citas")


@peluquero_or_above
def add_observation(request, id):
    cita = Cita.objects.filter(pk=id).first()
    if not cita:
        messages.error(request, "Appointment not found.")
        return redirect("list_citas")
    if cita.estado not in ("Pendiente", "Completada"):
        messages.error(request, "Observations can only be added to pending or completed appointments.")
        return redirect("list_citas")
    if request.method == "POST":
        observacion = (request.POST.get("observacion") or "").strip()
        if not observacion:
            messages.error(request, "Observation cannot be empty.")
            return redirect("list_citas")
        cita.observacion = observacion
        cita.fecha_observacion = timezone.now()
        cita.veterinario_observacion = request.session.get("user", "")
        cita.save()
        messages.success(request, "Observation added successfully.")
    return redirect("list_citas")


# --- Email reminder helpers ------------------------------------------------

def _build_appointment_pdf(cita):
    """Generate a PDF receipt for the appointment with tariff."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from django.conf import settings
    import io

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Get tariff by motivo (specific tariff type)
    tarifa = TarifaCita.objects.filter(tipo=cita.motivo, activo=True).first()
    precio = tarifa.precio if tarifa else 0

    # Header
    story.append(Paragraph("<b>RECIBO DE CITA AGENDADA</b>", styles['Heading1']))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"<b>{settings.BUSINESS_NAME}</b><br/>"
                          f"NIT: {settings.BUSINESS_NIT}<br/>"
                          f"Tel: {settings.BUSINESS_PHONE}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    # Appointment details
    propietario = cita.paciente.propietario if cita.paciente else None
    fecha_local = timezone.localtime(cita.fecha)

    story.append(Paragraph("<b>Detalles de la Cita</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2*cm))

    details_data = [
        ["Fecha", fecha_local.strftime("%d de %B de %Y")],
        ["Hora", fecha_local.strftime("%H:%M")],
        ["Mascota", cita.paciente.nombre if cita.paciente else "—"],
        ["Especie", cita.paciente.especie if cita.paciente else "—"],
        ["Propietario", propietario.nombre if propietario else "—"],
        ["Veterinario", cita.veterinario.nombre or cita.veterinario.user if cita.veterinario else "—"],
        ["Tipo de Consulta", cita.motivo or "Consulta General"],
    ]

    details_table = Table(details_data, colWidths=[3*cm, 10*cm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 0.5*cm))

    # Tariff section
    story.append(Paragraph("<b>Valor de la Consulta</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2*cm))

    tariff_data = [
        ["Concepto", "Valor"],
        [cita.motivo or "Consulta General", f"${precio:,.0f}"],
    ]

    tariff_table = Table(tariff_data, colWidths=[10*cm, 3*cm])
    tariff_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#65a30d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(tariff_table)
    story.append(Spacer(1, 0.3*cm))

    # Total
    total_data = [
        ["TOTAL A PAGAR", f"${precio:,.0f}"],
    ]
    total_table = Table(total_data, colWidths=[10*cm, 3*cm])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4d7c0f')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.5*cm))

    # Footer
    story.append(Paragraph(
        "<i>Documento generado electrónicamente. Confirmación de cita agendada.<br/>"
        "Por favor, llega 10 minutos antes de la hora indicada.</i>",
        styles['Normal']
    ))

    doc.build(story)
    return buf.getvalue()


def _send_appointment_reminder(cita):
    """Send appointment reminder email to owner with PDF receipt."""
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings

    # Get owner email — propietario is the correct field
    if not cita.paciente:
        return False
    propietario = cita.paciente.propietario
    if not propietario or not propietario.email:
        return False  # No email to send

    # Get tariff by motivo (specific tariff type)
    tarifa = TarifaCita.objects.filter(tipo=cita.motivo, activo=True).first()
    precio = tarifa.precio if tarifa else 0

    fecha_local = timezone.localtime(cita.fecha)

    # Context for email template
    ctx = {
        "propietario_nombre": propietario.nombre or "Propietario",
        "mascota_nombre": cita.paciente.nombre if cita.paciente else "—",
        "mascota_especie": cita.paciente.especie if cita.paciente else "—",
        "cita_fecha": fecha_local.strftime("%d de %B de %Y"),
        "cita_hora": fecha_local.strftime("%H:%M"),
        "veterinario_nombre": cita.veterinario.nombre or cita.veterinario.user if cita.veterinario else "—",
        "tipo_cita": cita.motivo or "Consulta General",
        "tarifa": f"{precio:,.0f}",
    }

    # Render HTML email
    html_content = render_to_string("emails/appointment_reminder.html", ctx)

    # Create email with PDF attachment
    subject = f"Recordatorio de Cita — {cita.paciente.nombre if cita.paciente else 'Tu Mascota'}"

    email = EmailMultiAlternatives(
        subject=subject,
        body=f"Recordatorio de cita para {cita.paciente.nombre if cita.paciente else 'tu mascota'} el {ctx['cita_fecha']} a las {ctx['cita_hora']}. Valor de la consulta: ${ctx['tarifa']}.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[propietario.email],
    )

    # Attach HTML alternative
    email.attach_alternative(html_content, "text/html")

    # Generate and attach PDF receipt
    pdf_bytes = _build_appointment_pdf(cita)
    mascota_nombre = cita.paciente.nombre.replace(" ", "_") if cita.paciente else "cita"
    fecha_str = fecha_local.strftime("%Y%m%d_%H%M")
    email.attach(f"Recibo_Cita_{mascota_nombre}_{fecha_str}.pdf", pdf_bytes, "application/pdf")

    # Send
    try:
        email.send(fail_silently=False)
        return True
    except Exception as exc:
        print(f"Error sending appointment reminder: {exc}")
        return False
