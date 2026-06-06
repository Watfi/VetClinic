"""Sales module — checkout, PDF invoice, email."""

import hashlib
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from home.models import Producto, Usuario, Venta, VentaItem

from ._helpers import admin_required, current_user


def _D(x, default=Decimal("0")):
    try:
        return Decimal(str(x).replace(",", "."))
    except (InvalidOperation, AttributeError, TypeError):
        return default


def _next_numero():
    last = Venta.objects.order_by("-id").first()
    n = (last.id + 1) if last else 1
    return f"F-{datetime.now().strftime('%Y%m%d')}-{n:05d}"


@admin_required
def list_ventas(request):
    ventas = Venta.objects.select_related("cliente").prefetch_related("items").all()
    return render(request, "ventas_list.html", {
        "ventas": ventas,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def add_venta(request):
    productos = Producto.objects.filter(activo=True, stock__gt=0)
    clientes = Usuario.objects.all()

    if request.method == "POST":
        items_json = request.POST.get("items_json") or "[]"
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []
        if not items:
            messages.error(request, "Agrega al menos un producto.")
            return redirect("add_venta")

        cliente_id = request.POST.get("cliente") or None
        cliente = Usuario.objects.filter(pk=cliente_id).first() if cliente_id else None

        cliente_nombre = (request.POST.get("cliente_nombre") or "").strip()
        cliente_email = (request.POST.get("cliente_email") or "").strip() or (
            cliente.email if cliente else ""
        )
        cliente_documento = (request.POST.get("cliente_documento") or "").strip()
        metodo_pago = request.POST.get("metodo_pago") or "Efectivo"
        impuestos_pct = _D(request.POST.get("impuestos_pct"), Decimal("0"))
        notas = (request.POST.get("notas") or "").strip()
        send_email = request.POST.get("send_email") == "on"

        with transaction.atomic():
            venta = Venta.objects.create(
                numero=_next_numero(),
                cliente=cliente,
                cliente_nombre=cliente_nombre,
                cliente_email=cliente_email,
                cliente_documento=cliente_documento,
                metodo_pago=metodo_pago,
                notas=notas,
                creado_por=current_user(request),
            )
            subtotal = Decimal("0")
            for it in items:
                pid = it.get("producto_id")
                cantidad = int(it.get("cantidad", 1))
                producto = Producto.objects.select_for_update().filter(pk=pid).first()
                if not producto:
                    continue
                if cantidad <= 0:
                    continue
                if producto.stock < cantidad:
                    messages.error(request, f"Stock insuficiente para {producto.nombre}.")
                    transaction.set_rollback(True)
                    return redirect("add_venta")
                # Allow per-sale custom price; fallback to product price
                custom_price = it.get("precio_unitario")
                if custom_price is not None:
                    try:
                        precio_venta = Decimal(str(custom_price)).quantize(Decimal("0.01"))
                    except (InvalidOperation, TypeError, ValueError):
                        precio_venta = producto.precio
                else:
                    precio_venta = producto.precio
                line_total = (precio_venta * cantidad).quantize(Decimal("0.01"))
                VentaItem.objects.create(
                    venta=venta,
                    producto=producto,
                    nombre=producto.nombre,
                    sku=producto.sku,
                    cantidad=cantidad,
                    precio_unitario=precio_venta,
                    precio_original=producto.precio,
                    subtotal=line_total,
                )
                producto.stock -= cantidad
                producto.save(update_fields=["stock"])
                subtotal += line_total

            impuestos = (subtotal * impuestos_pct / Decimal("100")).quantize(Decimal("0.01"))
            total = (subtotal + impuestos).quantize(Decimal("0.01"))
            venta.subtotal = subtotal
            venta.impuestos = impuestos
            venta.total = total
            venta.save()

        if send_email and venta.cliente_email:
            try:
                _send_invoice_email(venta)
                venta.factura_enviada = True
                venta.save(update_fields=["factura_enviada"])
                messages.success(request, f"Venta {venta.numero} registrada y factura enviada a {venta.cliente_email}.")
            except Exception as exc:
                messages.warning(request, f"Venta registrada, pero no se pudo enviar el email: {exc}")
        else:
            messages.success(request, f"Venta {venta.numero} registrada.")

        return redirect("view_venta", id=venta.id)

    return render(request, "ventas_form.html", {
        "productos": productos,
        "clientes": clientes,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def view_venta(request, id):
    venta = get_object_or_404(Venta.objects.prefetch_related("items"), pk=int(id))
    return render(request, "ventas_detail.html", {
        "venta": venta,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def cancel_venta(request, id):
    venta = get_object_or_404(Venta, pk=int(id))
    if venta.estado == "Anulada":
        messages.info(request, "La venta ya está anulada.")
        return redirect("view_venta", id=venta.id)
    with transaction.atomic():
        for item in venta.items.select_related("producto"):
            if item.producto:
                item.producto.stock += item.cantidad
                item.producto.save(update_fields=["stock"])
        venta.estado = "Anulada"
        venta.save(update_fields=["estado"])
    messages.success(request, "Venta anulada y stock restaurado.")
    return redirect("view_venta", id=venta.id)


@admin_required
def edit_venta(request, id):
    venta = get_object_or_404(Venta.objects.prefetch_related("items"), pk=int(id))
    if request.method == "POST":
        venta.cliente_nombre = (request.POST.get("cliente_nombre") or "").strip()
        venta.cliente_email = (request.POST.get("cliente_email") or "").strip()
        venta.cliente_documento = (request.POST.get("cliente_documento") or "").strip()
        venta.metodo_pago = request.POST.get("metodo_pago") or "Efectivo"
        venta.notas = (request.POST.get("notas") or "").strip()
        venta.save(update_fields=["cliente_nombre", "cliente_email", "cliente_documento", "metodo_pago", "notas"])
        messages.success(request, f"Venta {venta.numero} actualizada.")
        return redirect("view_venta", id=venta.id)
    return render(request, "ventas_edit.html", {
        "venta": venta,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def delete_venta(request, id):
    venta = get_object_or_404(Venta, pk=int(id))
    if request.method == "POST":
        numero = venta.numero
        with transaction.atomic():
            if venta.estado == "Pagada":
                for item in venta.items.select_related("producto"):
                    if item.producto:
                        item.producto.stock += item.cantidad
                        item.producto.save(update_fields=["stock"])
            venta.delete()
        messages.success(request, f"Venta {numero} eliminada y stock restaurado.")
    return redirect("list_ventas")


@admin_required
def invoice_pdf(request, id):
    venta = get_object_or_404(Venta.objects.prefetch_related("items"), pk=int(id))
    pdf_bytes = _build_invoice_pdf(venta)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{venta.numero}.pdf"'
    return resp


@admin_required
def resend_invoice(request, id):
    venta = get_object_or_404(Venta.objects.prefetch_related("items"), pk=int(id))
    if not venta.cliente_email:
        messages.error(request, "La venta no tiene email del cliente.")
        return redirect("view_venta", id=venta.id)
    try:
        _send_invoice_email(venta)
        venta.factura_enviada = True
        venta.save(update_fields=["factura_enviada"])
        messages.success(request, f"Factura reenviada a {venta.cliente_email}.")
    except Exception as exc:
        messages.error(request, f"No se pudo enviar el email: {exc}")
    return redirect("view_venta", id=venta.id)


def _cufe(venta):
    raw = f"{venta.numero}|{venta.total}|{venta.fecha.isoformat() if venta.fecha else ''}|{getattr(settings, 'BUSINESS_NIT', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_invoice_pdf(venta):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    business = getattr(settings, "BUSINESS_NAME", "Veterinaria")
    story.append(Paragraph(f"<b>{business}</b>", styles["Title"]))
    story.append(Paragraph("<b>FACTURA ELECTRÓNICA DE VENTA</b>", styles["Heading3"]))
    nit = getattr(settings, "BUSINESS_NIT", "")
    addr = getattr(settings, "BUSINESS_ADDRESS", "")
    city = getattr(settings, "BUSINESS_CITY", "")
    phone = getattr(settings, "BUSINESS_PHONE", "")
    regimen = getattr(settings, "BUSINESS_REGIMEN", "")
    resolucion = getattr(settings, "BUSINESS_RESOLUCION_DIAN", "")
    meta_lines = [x for x in [f"NIT: {nit}" if nit else "", addr, city, phone, regimen] if x]
    if meta_lines:
        story.append(Paragraph(" · ".join(meta_lines), styles["Normal"]))
    if resolucion:
        story.append(Paragraph(resolucion, styles["Normal"]))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph(f"<b>Factura {venta.numero}</b>", styles["Heading2"]))
    cufe = _cufe(venta)
    story.append(Paragraph(f"CUFE: {cufe}", styles["Normal"]))
    story.append(Paragraph(f"Fecha: {timezone.localtime(venta.fecha).strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Paragraph(f"Estado: {venta.estado}", styles["Normal"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Cliente</b>", styles["Heading4"]))
    story.append(Paragraph(f"Nombre: {venta.cliente_nombre or '-'}", styles["Normal"]))
    if venta.cliente_documento:
        story.append(Paragraph(f"Documento: {venta.cliente_documento}", styles["Normal"]))
    if venta.cliente_email:
        story.append(Paragraph(f"Email: {venta.cliente_email}", styles["Normal"]))
    story.append(Spacer(1, 0.4*cm))

    data = [["SKU", "Producto", "Cant.", "P. Unit.", "Subtotal"]]
    for it in venta.items.all():
        data.append([
            it.sku,
            it.nombre,
            str(it.cantidad),
            f"${it.precio_unitario:,.2f}",
            f"${it.subtotal:,.2f}",
        ])
    tbl = Table(data, colWidths=[3*cm, 7*cm, 2*cm, 2.7*cm, 2.7*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#556B2F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.4*cm))

    totals = [
        ["Subtotal", f"${venta.subtotal:,.2f}"],
        ["Impuestos", f"${venta.impuestos:,.2f}"],
        ["Total", f"${venta.total:,.2f}"],
    ]
    ttbl = Table(totals, colWidths=[12*cm, 5.4*cm])
    ttbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.black),
    ]))
    story.append(ttbl)

    if venta.notas:
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(f"<b>Notas:</b> {venta.notas}", styles["Normal"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(f"Método de pago: {venta.metodo_pago}", styles["Normal"]))
    story.append(Paragraph("Gracias por su compra.", styles["Italic"]))

    doc.build(story)
    return buf.getvalue()


def _send_invoice_email(venta, to=None, cc=None, subject=None, mensaje=None):
    """Send invoice PDF by email.

    `to` may be a string or list. `cc` is a list. Falls back to venta.cliente_email.
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string

    pdf_bytes = _build_invoice_pdf(venta)
    recipients = []
    if to:
        recipients = to if isinstance(to, list) else [t.strip() for t in to.split(",") if t.strip()]
    elif venta.cliente_email:
        recipients = [venta.cliente_email]
    if not recipients:
        raise ValueError("No hay destinatarios para enviar la factura.")

    cc_list = cc if isinstance(cc, list) else (
        [c.strip() for c in (cc or "").split(",") if c.strip()] if cc else []
    )

    business = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    subject_final = subject or f"Factura Electrónica {venta.numero} — {business}"
    mensaje_text = mensaje or f"Adjuntamos la factura electrónica {venta.numero} por un total de ${venta.total:,.2f}."

    ctx = {
        "venta": venta,
        "business": business,
        "business_nit": getattr(settings, "BUSINESS_NIT", ""),
        "business_phone": getattr(settings, "BUSINESS_PHONE", ""),
        "business_address": getattr(settings, "BUSINESS_ADDRESS", ""),
        "mensaje": mensaje_text,
        "items": list(venta.items.all()),
    }
    try:
        html_body = render_to_string("emails/invoice_email.html", ctx)
    except Exception:
        html_body = None

    text_body = (
        f"Hola {venta.cliente_nombre or ''},\n\n"
        f"{mensaje_text}\n\n"
        f"Total: ${venta.total:,.2f}\n"
        f"Método de pago: {venta.metodo_pago}\n\n"
        f"Gracias por su compra.\n{business}"
    )

    email = EmailMultiAlternatives(
        subject=subject_final,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        cc=cc_list,
    )
    if html_body:
        email.attach_alternative(html_body, "text/html")
    email.attach(f"factura_{venta.numero}.pdf", pdf_bytes, "application/pdf")
    email.send(fail_silently=False)
    return recipients


# --- Public API: send invoice email -----------------------------------------

@admin_required
def send_invoice_email(request, id):
    """POST endpoint with optional `to`, `cc`, `subject`, `mensaje` from a modal."""
    venta = get_object_or_404(Venta.objects.prefetch_related("items"), pk=int(id))
    if request.method != "POST":
        return redirect("view_venta", id=venta.id)

    to = request.POST.get("to") or venta.cliente_email
    cc = request.POST.get("cc") or ""
    subject = request.POST.get("subject") or ""
    mensaje = request.POST.get("mensaje") or ""

    try:
        recipients = _send_invoice_email(venta, to=to, cc=cc, subject=subject, mensaje=mensaje)
        venta.factura_enviada = True
        venta.factura_enviada_at = timezone.now()
        venta.factura_enviada_to = ", ".join(recipients)[:300]
        venta.save(update_fields=["factura_enviada", "factura_enviada_at", "factura_enviada_to"])
        messages.success(request, f"Factura enviada a {', '.join(recipients)}.")
    except Exception as exc:
        messages.error(request, f"No se pudo enviar el email: {exc}")
    return redirect("view_venta", id=venta.id)
