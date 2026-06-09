"""Inventory module — categorias, productos y movimientos."""

import io
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
try:
    from reportlab.platypus import Image as RLImage
except ImportError:
    RLImage = None

from home.models import Categoria, HistorialPrecio, MovimientoInventario, Producto, Usuario

from ._helpers import admin_required


@admin_required
def list_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, "categorias_list.html", {
        "categorias": categorias,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def add_categoria(request):
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        if not nombre:
            messages.error(request, "Nombre requerido.")
            return redirect("add_categoria")
        if Categoria.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, "Ya existe una categoría con ese nombre.")
            return redirect("list_categorias")
        Categoria.objects.create(
            nombre=nombre,
            descripcion=(request.POST.get("descripcion") or "").strip(),
        )
        messages.success(request, "Categoría creada.")
        return redirect("list_categorias")
    return render(request, "categorias_form.html", {
        "categoria": None,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def edit_categoria(request, id):
    categoria = get_object_or_404(Categoria, pk=int(id))
    if request.method == "POST":
        categoria.nombre = (request.POST.get("nombre") or categoria.nombre).strip()
        categoria.descripcion = (request.POST.get("descripcion") or "").strip()
        categoria.save()
        messages.success(request, "Categoría actualizada.")
        return redirect("list_categorias")
    return render(request, "categorias_form.html", {
        "categoria": categoria,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def delete_categoria(request, id):
    categoria = get_object_or_404(Categoria, pk=int(id))
    categoria.delete()
    messages.success(request, "Categoría eliminada.")
    return redirect("list_categorias")


@admin_required
def list_productos(request):
    productos = Producto.objects.select_related("categoria").all()
    q = (request.GET.get("q") or "").strip()
    if q:
        productos = productos.filter(nombre__icontains=q) | productos.filter(sku__icontains=q)
    return render(request, "productos_list.html", {
        "productos": productos,
        "q": q,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


def _parse_decimal(value, default=Decimal("0")):
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, AttributeError, TypeError):
        return default


def _parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@admin_required
def add_producto(request):
    categorias = Categoria.objects.all()
    if request.method == "POST":
        sku = (request.POST.get("sku") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        if not sku or not nombre:
            messages.error(request, "SKU y nombre son obligatorios.")
            return redirect("add_producto")
        if Producto.objects.filter(sku__iexact=sku).exists():
            messages.error(request, "Ya existe un producto con ese SKU.")
            return redirect("add_producto")
        cat_id = request.POST.get("categoria") or None
        Producto.objects.create(
            sku=sku,
            nombre=nombre,
            descripcion=(request.POST.get("descripcion") or "").strip(),
            categoria_id=int(cat_id) if cat_id else None,
            precio_compra=_parse_decimal(request.POST.get("precio_compra")),
            precio=_parse_decimal(request.POST.get("precio")),
            stock=_parse_int(request.POST.get("stock")),
            stock_minimo=_parse_int(request.POST.get("stock_minimo")),
            activo=request.POST.get("activo") == "on",
        )
        messages.success(request, "Producto creado.")
        return redirect("list_productos")
    return render(request, "productos_form.html", {
        "producto": None,
        "categorias": categorias,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def edit_producto(request, id):
    producto = get_object_or_404(Producto, pk=int(id))
    categorias = Categoria.objects.all()
    if request.method == "POST":
        precio_venta_ant = producto.precio
        precio_compra_ant = producto.precio_compra
        producto.sku = (request.POST.get("sku") or producto.sku).strip()
        producto.nombre = (request.POST.get("nombre") or producto.nombre).strip()
        producto.descripcion = (request.POST.get("descripcion") or "").strip()
        cat_id = request.POST.get("categoria") or None
        producto.categoria_id = int(cat_id) if cat_id else None
        producto.precio_compra = _parse_decimal(request.POST.get("precio_compra"), producto.precio_compra)
        producto.precio = _parse_decimal(request.POST.get("precio"), producto.precio)
        producto.stock = _parse_int(request.POST.get("stock"), producto.stock)
        producto.stock_minimo = _parse_int(request.POST.get("stock_minimo"), producto.stock_minimo)
        producto.activo = request.POST.get("activo") == "on"
        producto.save()
        username = request.session.get("user")
        usuario = Usuario.objects.filter(user=username).first()
        if producto.precio != precio_venta_ant:
            HistorialPrecio.objects.create(
                producto=producto, tipo="precio_venta",
                precio_anterior=precio_venta_ant, precio_nuevo=producto.precio,
                usuario=usuario,
            )
        if producto.precio_compra != precio_compra_ant:
            HistorialPrecio.objects.create(
                producto=producto, tipo="precio_compra",
                precio_anterior=precio_compra_ant, precio_nuevo=producto.precio_compra,
                usuario=usuario,
            )
        messages.success(request, "Producto actualizado.")
        return redirect("list_productos")
    return render(request, "productos_form.html", {
        "producto": producto,
        "categorias": categorias,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def delete_producto(request, id):
    producto = get_object_or_404(Producto, pk=int(id))
    producto.delete()
    messages.success(request, "Producto eliminado.")
    return redirect("list_productos")


# ── Movimientos de inventario ──────────────────────────────────────────────

@admin_required
def list_movimientos(request, producto_id):
    producto = get_object_or_404(Producto, pk=int(producto_id))
    movimientos = producto.movimientos.select_related("usuario").all()
    return render(request, "movimientos_list.html", {
        "producto": producto,
        "movimientos": movimientos,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def add_entrada(request, producto_id):
    import base64 as _b64
    producto = get_object_or_404(Producto, pk=int(producto_id))
    if request.method == "POST":
        cantidad = _parse_int(request.POST.get("cantidad"), 0)
        if cantidad <= 0:
            messages.error(request, "La cantidad debe ser mayor a 0.")
            return redirect("add_entrada", producto_id=producto.id)

        username = request.session.get("user")
        usuario = Usuario.objects.filter(user=username).first()

        fecha_factura = request.POST.get("fecha_factura") or None
        fecha_pago = request.POST.get("fecha_pago") or None

        # Handle file as base64 so it works on read-only filesystems (Vercel)
        archivo_b64 = None
        if request.FILES.get("archivo_factura"):
            f = request.FILES["archivo_factura"]
            content_type = f.content_type or "application/octet-stream"
            data = _b64.b64encode(f.read()).decode("utf-8")
            archivo_b64 = f"data:{content_type};base64,{data};name={f.name}"

        mov = MovimientoInventario.objects.create(
            producto=producto,
            tipo="Entrada",
            cantidad=cantidad,
            usuario=usuario,
            nombre_factura=(request.POST.get("nombre_factura") or "").strip(),
            numero_factura=(request.POST.get("numero_factura") or "").strip(),
            fecha_factura=fecha_factura if fecha_factura else None,
            fecha_pago=fecha_pago if fecha_pago else None,
            pago_pendiente=request.POST.get("pago_pendiente") == "on",
            proveedor=(request.POST.get("proveedor") or "").strip(),
            nit_proveedor=(request.POST.get("nit_proveedor") or "").strip(),
            notas=(request.POST.get("notas") or "").strip(),
            archivo_factura=archivo_b64,
        )

        producto.stock += cantidad
        producto.save(update_fields=["stock"])
        messages.success(request, f"Entrada registrada: +{cantidad} unidades.")
        return redirect("list_movimientos", producto_id=producto.id)

    return render(request, "movimiento_entrada_form.html", {
        "producto": producto,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def add_salida(request, producto_id):
    producto = get_object_or_404(Producto, pk=int(producto_id))
    if request.method == "POST":
        cantidad = _parse_int(request.POST.get("cantidad"), 0)
        if cantidad <= 0:
            messages.error(request, "La cantidad debe ser mayor a 0.")
            return redirect("add_salida", producto_id=producto.id)
        if cantidad > producto.stock:
            messages.error(request, f"Stock insuficiente. Disponible: {producto.stock}.")
            return redirect("add_salida", producto_id=producto.id)

        username = request.session.get("user")
        usuario = Usuario.objects.filter(user=username).first()

        MovimientoInventario.objects.create(
            producto=producto,
            tipo="Salida",
            cantidad=cantidad,
            usuario=usuario,
            motivo=(request.POST.get("motivo") or "").strip(),
            notas=(request.POST.get("notas") or "").strip(),
        )
        producto.stock -= cantidad
        producto.save(update_fields=["stock"])
        messages.success(request, f"Salida registrada: -{cantidad} unidades.")
        return redirect("list_movimientos", producto_id=producto.id)

    return render(request, "movimiento_salida_form.html", {
        "producto": producto,
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
    })


@admin_required
def toggle_descuento(request, producto_id):
    """AJAX POST — toggle discount on/off and set percentage without changing base price."""
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    producto = get_object_or_404(Producto, pk=int(producto_id))
    activo = request.POST.get("descuento_activo") == "1"
    try:
        porcentaje = int(request.POST.get("descuento_porcentaje") or 0)
    except ValueError:
        porcentaje = 0
    porcentaje = max(0, min(porcentaje, 100))
    desc_ant = producto.descuento_activo
    producto.descuento_activo = activo
    producto.descuento_porcentaje = porcentaje
    producto.save(update_fields=["descuento_activo", "descuento_porcentaje"])
    username = request.session.get("user")
    usuario = Usuario.objects.filter(user=username).first()
    if activo != desc_ant or (activo and porcentaje > 0):
        tipo_h = "descuento_activado" if activo else "descuento_desactivado"
        HistorialPrecio.objects.create(
            producto=producto, tipo=tipo_h,
            precio_anterior=producto.precio,
            precio_nuevo=producto.precio_con_descuento,
            descuento_porcentaje=porcentaje,
            usuario=usuario,
            notas=f"Descuento {'activado' if activo else 'desactivado'}: {porcentaje}%",
        )
    precio_final = float(producto.precio_con_descuento) if activo and porcentaje > 0 else float(producto.precio)
    return JsonResponse({
        "ok": True,
        "descuento_activo": activo,
        "descuento_porcentaje": porcentaje,
        "precio_original": float(producto.precio),
        "precio_final": round(precio_final, 2),
    })


@admin_required
def entrada_pdf(request, mov_id):
    """PDF de comprobante de entrada de inventario con encabezado Kane Agropet."""
    mov = get_object_or_404(
        MovimientoInventario.objects.select_related("producto", "usuario"),
        pk=int(mov_id), tipo="Entrada",
    )
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold", spaceAfter=2)
    sub_s   = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#444444"))
    label_s = ParagraphStyle("L", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold", textColor=colors.HexColor("#556B2F"))
    value_s = ParagraphStyle("V", parent=styles["Normal"], fontSize=9)
    head_s  = ParagraphStyle("H", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#2d4a1e"))

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

    fecha_str = timezone.localtime(mov.fecha).strftime("%d/%m/%Y %H:%M") if mov.fecha else ""
    header_tbl = Table(
        [[logo_cell, Paragraph(biz_lines, title_s),
          Paragraph(f"<b>COMPROBANTE DE ENTRADA</b><br/>Fecha: {fecha_str}", sub_s)]],
        colWidths=[3*cm, 9.5*cm, 5.5*cm],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("LINEBELOW", (0,0), (-1,-1), 1, colors.HexColor("#556B2F")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Producto ────────────────────────────────────────────────────────────
    prod = mov.producto
    prod_data = [
        [Paragraph("<b>PRODUCTO</b>", head_s), "", "", ""],
        [Paragraph("Nombre:", label_s), Paragraph(prod.nombre if prod else "—", value_s),
         Paragraph("SKU:", label_s),    Paragraph(prod.sku if prod else "—", value_s)],
        [Paragraph("Categoría:", label_s), Paragraph(prod.categoria.nombre if prod and prod.categoria else "—", value_s),
         Paragraph("Cantidad entrada:", label_s), Paragraph(str(mov.cantidad), value_s)],
    ]
    prod_tbl = Table(prod_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    prod_tbl.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f4ea")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(prod_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Factura / Proveedor ─────────────────────────────────────────────────
    fact_data = [
        [Paragraph("<b>DATOS DE COMPRA</b>", head_s), "", "", ""],
        [Paragraph("Nombre factura:", label_s), Paragraph(mov.nombre_factura or "—", value_s),
         Paragraph("N° Factura:", label_s),     Paragraph(mov.numero_factura or "—", value_s)],
        [Paragraph("Proveedor:", label_s),      Paragraph(mov.proveedor or "—", value_s),
         Paragraph("NIT proveedor:", label_s),  Paragraph(mov.nit_proveedor or "—", value_s)],
        [Paragraph("Fecha factura:", label_s),  Paragraph(str(mov.fecha_factura) if mov.fecha_factura else "—", value_s),
         Paragraph("Fecha pago:", label_s),     Paragraph(str(mov.fecha_pago) if mov.fecha_pago else "—", value_s)],
        [Paragraph("Pago pendiente:", label_s), Paragraph("Sí" if mov.pago_pendiente else "No", value_s), "", ""],
    ]
    fact_tbl = Table(fact_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    fact_tbl.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("SPAN", (1,4), (-1,4)),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f4ea")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(fact_tbl)

    if mov.notas:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"<b>Notas:</b> {mov.notas}", value_s))

    # ── Archivo adjunto (imagen) ────────────────────────────────────────────
    if mov.archivo_factura:
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#556B2F"), spaceAfter=0.3*cm))
        story.append(Paragraph("<b>FACTURA ADJUNTA</b>", head_s))
        story.append(Spacer(1, 0.2*cm))
        try:
            import base64 as _b64
            raw = mov.archivo_factura  # "data:<mime>;base64,<data>;name=<filename>"
            if raw and raw.startswith("data:"):
                # Parse data URI: data:<mime>;base64,<data>;name=<name>
                header, b64data = raw.split(",", 1)
                # Strip optional ;name=... suffix from b64data
                if ";name=" in b64data:
                    b64data = b64data.split(";name=")[0]
                mime = header.split(":")[1].split(";")[0]
                file_bytes = _b64.b64decode(b64data)
                if mime in ("image/jpeg", "image/png", "image/gif", "image/webp") and RLImage:
                    img_buf = io.BytesIO(file_bytes)
                    img = RLImage(img_buf, width=15*cm, height=10*cm)
                    img.hAlign = "LEFT"
                    story.append(img)
                else:
                    story.append(Paragraph(f"Archivo adjunto (tipo: {mime}) — no es imagen, no se puede incrustar en PDF.", value_s))
            else:
                story.append(Paragraph("Archivo adjunto no disponible.", value_s))
        except Exception as e:
            story.append(Paragraph(f"No se pudo cargar el archivo adjunto: {e}", value_s))

    # ── Registrado por ──────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black, spaceAfter=0.1*cm, hAlign="LEFT"))
    usuario_nombre = (mov.usuario.nombre or mov.usuario.user) if mov.usuario else "—"
    story.append(Paragraph(f"<b>{usuario_nombre}</b>", value_s))
    story.append(Paragraph("Registrado por", ParagraphStyle("sm", parent=styles["Normal"], fontSize=8, textColor=colors.grey)))

    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="entrada_{mov.id}.pdf"'
    return resp


@admin_required
def historial_precios_pdf(request, producto_id):
    """PDF con historial completo de precios de un producto."""
    producto = get_object_or_404(Producto, pk=int(producto_id))
    historial = HistorialPrecio.objects.filter(producto=producto).select_related("usuario").order_by("-fecha")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold", spaceAfter=2)
    sub_s   = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#444444"))
    label_s = ParagraphStyle("L", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold", textColor=colors.HexColor("#556B2F"))
    value_s = ParagraphStyle("V", parent=styles["Normal"], fontSize=9)
    head_s  = ParagraphStyle("H", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#2d4a1e"))

    story = []

    # ── Encabezado Kane Agropet ──────────────────────────────────────────────
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

    from django.utils import timezone as _tz
    fecha_gen = _tz.localtime(_tz.now()).strftime("%d/%m/%Y %H:%M")
    header_tbl = Table(
        [[logo_cell, Paragraph(biz_lines, title_s),
          Paragraph(f"<b>HISTORIAL DE PRECIOS</b><br/>Generado: {fecha_gen}", sub_s)]],
        colWidths=[3*cm, 9.5*cm, 5.5*cm],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("LINEBELOW", (0,0), (-1,-1), 1, colors.HexColor("#556B2F")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Info actual del producto ─────────────────────────────────────────────
    story.append(Paragraph("<b>INFORMACIÓN ACTUAL DEL PRODUCTO</b>", head_s))
    story.append(Spacer(1, 0.2*cm))
    info_data = [
        [Paragraph("Nombre:", label_s), Paragraph(producto.nombre, value_s),
         Paragraph("SKU:", label_s),    Paragraph(producto.sku, value_s)],
        [Paragraph("Categoría:", label_s), Paragraph(producto.categoria.nombre if producto.categoria else "—", value_s),
         Paragraph("Estado:", label_s), Paragraph("Activo" if producto.activo else "Inactivo", value_s)],
        [Paragraph("Precio compra:", label_s), Paragraph(f"${producto.precio_compra}", value_s),
         Paragraph("Precio venta:", label_s),  Paragraph(f"${producto.precio}", value_s)],
        [Paragraph("Descuento activo:", label_s),
         Paragraph(f"Sí — {producto.descuento_porcentaje}% → ${producto.precio_con_descuento:.2f}" if producto.descuento_activo else "No", value_s),
         Paragraph("Stock:", label_s), Paragraph(str(producto.stock), value_s)],
    ]
    info_tbl = Table(info_data, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f8faf5")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#556B2F"), spaceAfter=0.3*cm))

    # ── Tabla historial ──────────────────────────────────────────────────────
    story.append(Paragraph("<b>HISTORIAL DE CAMBIOS DE PRECIO</b>", head_s))
    story.append(Spacer(1, 0.2*cm))

    TIPO_LABELS = {
        "precio_venta":         "Cambio precio venta",
        "precio_compra":        "Cambio precio compra",
        "descuento_activado":   "Descuento activado",
        "descuento_desactivado":"Descuento desactivado",
    }
    TIPO_COLORS = {
        "precio_venta":         colors.HexColor("#e8f5e9"),
        "precio_compra":        colors.HexColor("#e3f2fd"),
        "descuento_activado":   colors.HexColor("#fce4ec"),
        "descuento_desactivado":colors.HexColor("#f3e5f5"),
    }

    if historial:
        hdr_s = ParagraphStyle("Hdr", parent=styles["Normal"], fontSize=8,
                               fontName="Helvetica-Bold", textColor=colors.white)
        h_data = [[
            Paragraph("Fecha", hdr_s),
            Paragraph("Tipo de cambio", hdr_s),
            Paragraph("Precio anterior", hdr_s),
            Paragraph("Precio nuevo", hdr_s),
            Paragraph("Descuento %", hdr_s),
            Paragraph("Usuario", hdr_s),
        ]]
        row_colors = []
        for idx, h in enumerate(historial, 1):
            fecha_h = timezone.localtime(h.fecha).strftime("%d/%m/%Y %H:%M") if h.fecha else "—"
            usuario_h = (h.usuario.nombre or h.usuario.user) if h.usuario else "—"
            tipo_label = TIPO_LABELS.get(h.tipo, h.tipo)
            precio_ant = f"${h.precio_anterior:.2f}" if h.precio_anterior is not None else "—"
            precio_new = f"${h.precio_nuevo:.2f}" if h.precio_nuevo is not None else "—"
            desc_pct = f"{h.descuento_porcentaje}%" if h.descuento_porcentaje else "—"
            h_data.append([
                Paragraph(fecha_h, ParagraphStyle("xs", parent=styles["Normal"], fontSize=7)),
                Paragraph(tipo_label, ParagraphStyle("xs2", parent=styles["Normal"], fontSize=8)),
                Paragraph(precio_ant, ParagraphStyle("xs3", parent=styles["Normal"], fontSize=8)),
                Paragraph(precio_new, ParagraphStyle("xs4", parent=styles["Normal"], fontSize=8)),
                Paragraph(desc_pct, ParagraphStyle("xs5", parent=styles["Normal"], fontSize=8)),
                Paragraph(usuario_h, ParagraphStyle("xs6", parent=styles["Normal"], fontSize=7)),
            ])
            row_colors.append(TIPO_COLORS.get(h.tipo, colors.white))

        h_tbl = Table(h_data, colWidths=[3.5*cm, 4*cm, 3*cm, 3*cm, 2.5*cm, 3*cm])
        tbl_style = [
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#556B2F")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]
        for i, bg in enumerate(row_colors, 1):
            tbl_style.append(("BACKGROUND", (0,i), (-1,i), bg))
        h_tbl.setStyle(TableStyle(tbl_style))
        story.append(h_tbl)
    else:
        story.append(Paragraph("Sin registros de cambios de precio aún.", value_s))

    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="historial_precios_{producto.sku}.pdf"'
    return resp
