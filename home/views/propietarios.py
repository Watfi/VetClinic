"""Propietarios CRUD + Mascotas CRUD vinculadas a propietario."""

import base64
import io
import os

from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render

from home.models import (Paciente, Propietario, Vacuna, Desparasitacion,
                         HistoriaClinica, Receta, RecetaItem, Usuario,
                         Cirugia, ExamenLaboratorio, Seguimiento,
                         Orden, ImagenDiagnostica, Documento, Remision, Peluqueria,
                         AdjuntoArchivo)

from ._helpers import admin_required, vet_or_admin_required, current_user


_ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _prop_to_dict(p):
    return {
        "id": p.id,
        "nombre": p.nombre,
        "tipo_documento": p.tipo_documento,
        "tipo_documento_display": p.get_tipo_documento_display() if p.tipo_documento else "",
        "numero_documento": p.numero_documento,
        "telefono": p.telefono,
        "email": p.email,
        "direccion": p.direccion,
        "ciudad": p.ciudad,
        "contacto_autorizado": p.contacto_autorizado,
        "telefono_alternativo": p.telefono_alternativo,
        "notas": p.notas,
        "fecha_registro": p.fecha_registro,
        "num_mascotas": p.mascotas.count(),
    }


def _mascota_to_dict(m):
    prop = m.propietario
    return {
        "id": m.id,
        "nombre": m.nombre,
        "codigo_chip": m.codigo_chip,
        "especie": m.especie,
        "raza": m.raza,
        "sexo": m.sexo,
        "color": m.color,
        "fecha_nacimiento": m.fecha_nacimiento.strftime("%Y-%m-%d") if m.fecha_nacimiento else "",
        "peso": str(m.peso) if m.peso else "",
        "unidad_peso": m.unidad_peso,
        "talla": m.talla,
        "estado_reproductivo": m.estado_reproductivo,
        "alimento": m.alimento,
        "profile_picture": m.profile_picture,
        "propietario_id": prop.id if prop else None,
        "propietario_nombre": prop.nombre if prop else "",
        "propietario_telefono": prop.telefono if prop else "",
        "propietario_email": prop.email if prop else "",
        "propietario_documento": prop.numero_documento if prop else "",
    }


def _decode_picture(request):
    if "profile_picture" not in request.FILES:
        return None, None
    pic = request.FILES["profile_picture"]
    if pic.size == 0:
        return None, None
    if pic.content_type not in _ALLOWED_IMAGE_TYPES:
        return None, "Tipo de archivo inválido. Solo JPG, PNG, GIF y WEBP."
    if pic.size > _MAX_IMAGE_BYTES:
        return None, "El archivo debe ser menor a 5MB."
    encoded = base64.b64encode(pic.read()).decode("utf-8")
    return f"data:{pic.content_type};base64,{encoded}", None


# ─────────────────────────────────────────────
# Propietarios CRUD
# ─────────────────────────────────────────────

@vet_or_admin_required
def list_propietarios(request):
    props = Propietario.objects.prefetch_related("mascotas").all()
    data = [_prop_to_dict(p) for p in props]
    return render(request, "propietarios_list.html", {
        "propietarios": data,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def add_propietario(request):
    if request.method == "POST":
        p = Propietario(
            nombre=(request.POST.get("nombre") or "").strip(),
            tipo_documento=(request.POST.get("tipo_documento") or "").strip(),
            numero_documento=(request.POST.get("numero_documento") or "").strip(),
            telefono=(request.POST.get("telefono") or "").strip(),
            email=(request.POST.get("email") or "").strip(),
            direccion=(request.POST.get("direccion") or "").strip(),
            ciudad=(request.POST.get("ciudad") or "").strip(),
            contacto_autorizado=(request.POST.get("contacto_autorizado") or "").strip(),
            telefono_alternativo=(request.POST.get("telefono_alternativo") or "").strip(),
            notas=(request.POST.get("notas") or "").strip(),
        )
        p.save()
        messages.success(request, f"Propietario '{p.nombre or p.numero_documento or 'Sin nombre'}' registrado correctamente.")
        if request.POST.get("add_mascota"):
            return redirect("add_mascota", propietario_id=p.id)
        return redirect("list_pacientes")

    return render(request, "propietario_form.html", {
        "action": "Agregar",
        "propietario": {},
        "tipo_doc_choices": Propietario.TIPO_DOC_CHOICES,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def edit_propietario(request, id):
    p = Propietario.objects.filter(pk=id).first()
    if not p:
        messages.error(request, "Propietario no encontrado.")
        return redirect("list_pacientes")

    if request.method == "POST":
        p.nombre = (request.POST.get("nombre") or "").strip()
        p.tipo_documento = (request.POST.get("tipo_documento") or "").strip()
        p.numero_documento = (request.POST.get("numero_documento") or "").strip()
        p.telefono = (request.POST.get("telefono") or "").strip()
        p.email = (request.POST.get("email") or "").strip()
        p.direccion = (request.POST.get("direccion") or "").strip()
        p.ciudad = (request.POST.get("ciudad") or "").strip()
        p.contacto_autorizado = (request.POST.get("contacto_autorizado") or "").strip()
        p.telefono_alternativo = (request.POST.get("telefono_alternativo") or "").strip()
        p.notas = (request.POST.get("notas") or "").strip()
        p.save()
        messages.success(request, "Propietario actualizado correctamente.")
        return redirect("list_pacientes")

    return render(request, "propietario_form.html", {
        "action": "Editar",
        "propietario": _prop_to_dict(p),
        "tipo_doc_choices": Propietario.TIPO_DOC_CHOICES,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def delete_propietario(request, id):
    p = Propietario.objects.filter(pk=id).first()
    if not p:
        messages.error(request, "Propietario no encontrado.")
        return redirect("list_pacientes")
    nombre = p.nombre or p.numero_documento or f"#{p.id}"
    p.delete()
    messages.info(request, f"Propietario '{nombre}' eliminado.")
    return redirect("list_pacientes")


# ─────────────────────────────────────────────
# Mascotas CRUD (vinculadas a propietario)
# ─────────────────────────────────────────────

@vet_or_admin_required
def mascotas_propietario(request, propietario_id):
    prop = Propietario.objects.filter(pk=propietario_id).first()
    if not prop:
        messages.error(request, "Propietario no encontrado.")
        return redirect("list_pacientes")
    mascotas = [_mascota_to_dict(m) for m in prop.mascotas.all()]
    return render(request, "mascotas_propietario.html", {
        "propietario": _prop_to_dict(prop),
        "mascotas": mascotas,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def add_mascota(request, propietario_id):
    prop = Propietario.objects.filter(pk=propietario_id).first()
    if not prop:
        messages.error(request, "Propietario no encontrado.")
        return redirect("list_pacientes")

    if request.method == "POST":
        picture, err = _decode_picture(request)
        if err:
            messages.error(request, err)
            return redirect("add_mascota", propietario_id=propietario_id)

        fecha_nac = None
        fecha_str = (request.POST.get("fecha_nacimiento") or "").strip()
        if fecha_str:
            from datetime import datetime as dt
            try:
                fecha_nac = dt.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        peso_val = None
        peso_str = (request.POST.get("peso") or "").strip()
        if peso_str:
            try:
                peso_val = float(peso_str)
            except ValueError:
                pass

        m = Paciente(
            propietario=prop,
            nombre=(request.POST.get("nombre") or "").strip(),
            codigo_chip=(request.POST.get("codigo_chip") or "").strip(),
            especie=(request.POST.get("especie") or "").strip(),
            raza=(request.POST.get("raza") or "").strip(),
            sexo=(request.POST.get("sexo") or "Desconocido").strip(),
            color=(request.POST.get("color") or "").strip(),
            fecha_nacimiento=fecha_nac,
            peso=peso_val,
            unidad_peso=(request.POST.get("unidad_peso") or "kg").strip(),
            talla=(request.POST.get("talla") or "").strip(),
            estado_reproductivo=(request.POST.get("estado_reproductivo") or "").strip(),
            alimento=(request.POST.get("alimento") or "").strip(),
            profile_picture=picture,
        )
        m.save()
        messages.success(request, f"Mascota '{m.nombre or 'Sin nombre'}' registrada correctamente.")
        return redirect("mascotas_propietario", propietario_id=propietario_id)

    return render(request, "mascota_form.html", {
        "action": "Registrar",
        "propietario": _prop_to_dict(prop),
        "mascota": {},
        "sexo_choices": Paciente.SEXO_CHOICES,
        "talla_choices": Paciente.TALLA_CHOICES,
        "estado_reproductivo_choices": Paciente.ESTADO_REPRODUCTIVO_CHOICES,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def edit_mascota(request, id):
    m = Paciente.objects.select_related("propietario").filter(pk=id).first()
    if not m:
        messages.error(request, "Mascota no encontrada.")
        return redirect("list_pacientes")

    if request.method == "POST":
        picture, err = _decode_picture(request)
        if err:
            messages.error(request, err)

        fecha_nac = None
        fecha_str = (request.POST.get("fecha_nacimiento") or "").strip()
        if fecha_str:
            from datetime import datetime as dt
            try:
                fecha_nac = dt.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        peso_val = None
        peso_str = (request.POST.get("peso") or "").strip()
        if peso_str:
            try:
                peso_val = float(peso_str)
            except ValueError:
                pass

        m.nombre = (request.POST.get("nombre") or "").strip()
        m.codigo_chip = (request.POST.get("codigo_chip") or "").strip()
        m.especie = (request.POST.get("especie") or "").strip()
        m.raza = (request.POST.get("raza") or "").strip()
        m.sexo = (request.POST.get("sexo") or "Desconocido").strip()
        m.color = (request.POST.get("color") or "").strip()
        m.fecha_nacimiento = fecha_nac
        m.peso = peso_val
        m.unidad_peso = (request.POST.get("unidad_peso") or "kg").strip()
        m.talla = (request.POST.get("talla") or "").strip()
        m.estado_reproductivo = (request.POST.get("estado_reproductivo") or "").strip()
        m.alimento = (request.POST.get("alimento") or "").strip()

        if request.POST.get("remove_profile_picture") == "true":
            m.profile_picture = None
        elif picture:
            m.profile_picture = picture

        m.save()
        messages.success(request, "Mascota actualizada correctamente.")
        if m.propietario_id:
            return redirect("mascotas_propietario", propietario_id=m.propietario_id)
        return redirect("list_pacientes")

    prop = m.propietario
    return render(request, "mascota_form.html", {
        "action": "Editar",
        "propietario": _prop_to_dict(prop) if prop else {},
        "mascota": _mascota_to_dict(m),
        "sexo_choices": Paciente.SEXO_CHOICES,
        "talla_choices": Paciente.TALLA_CHOICES,
        "estado_reproductivo_choices": Paciente.ESTADO_REPRODUCTIVO_CHOICES,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
    })


@vet_or_admin_required
def delete_mascota(request, id):
    m = Paciente.objects.filter(pk=id).first()
    if not m:
        messages.error(request, "Mascota no encontrada.")
        return redirect("list_pacientes")
    prop_id = m.propietario_id
    nombre = m.nombre or f"#{m.id}"
    m.delete()
    messages.info(request, f"Mascota '{nombre}' eliminada.")
    if prop_id:
        return redirect("mascotas_propietario", propietario_id=prop_id)
    return redirect("list_pacientes")


# ─────────────────────────────────────────────
# Historia Clínica por paciente (OKVet-style)
# ─────────────────────────────────────────────

@vet_or_admin_required
def historia_paciente(request, paciente_id):
    m = Paciente.objects.select_related("propietario").filter(pk=paciente_id).first()
    if not m:
        messages.error(request, "Mascota no encontrada.")
        return redirect("list_pacientes")

    tab = request.GET.get("tab", "historia")

    consultas = list(HistoriaClinica.objects.filter(paciente=m).order_by("-fecha"))
    consulta_ids = [c.id for c in consultas]
    _adj_map = {}
    for adj in AdjuntoArchivo.objects.filter(tipo="consulta", object_id__in=consulta_ids):
        _adj_map.setdefault(adj.object_id, []).append(adj)
    for c in consultas:
        c.adjuntos_list = _adj_map.get(c.id, [])
    vacunas = list(Vacuna.objects.filter(paciente=m))
    desparasitaciones = list(Desparasitacion.objects.filter(paciente=m))
    recetas = list(Receta.objects.filter(paciente=m).select_related("veterinario").prefetch_related("items"))
    cirugias = list(Cirugia.objects.filter(paciente=m).select_related("veterinario"))
    examenes = list(ExamenLaboratorio.objects.filter(paciente=m).select_related("veterinario"))
    seguimientos = list(Seguimiento.objects.filter(paciente=m).select_related("veterinario"))
    citas = list(m.citas.all())
    ordenes = list(Orden.objects.filter(paciente=m).select_related("veterinario"))
    imagenes = list(ImagenDiagnostica.objects.filter(paciente=m).select_related("veterinario"))
    documentos = list(Documento.objects.filter(paciente=m))
    remisiones = list(Remision.objects.filter(paciente=m).select_related("veterinario"))
    peluquerias = list(Peluqueria.objects.filter(paciente=m).select_related("veterinario"))

    vets = list(Usuario.objects.filter(ofrece_consulta_medica=True))

    # ── Timeline unificado (para Historia general) ──
    from django.urls import reverse as _rev
    from datetime import date as _date

    def _s(obj, attr, default=""):
        return str(getattr(obj, attr, None) or default)

    tl = []

    for c in consultas:
        detalles = []
        if c.hc_numero: detalles.append(f"HC #{c.hc_numero}")
        if c.motivo_consulta: detalles.append(c.motivo_consulta)
        if c.subjetivo: detalles.append(f"S: {c.subjetivo[:80]}")
        if c.interpretacion: detalles.append(f"Dx: {c.interpretacion[:80]}")
        tl.append({
            'tipo': 'Consulta', 'icon': 'fa-stethoscope', 'badge': 'bg-olive-700/80 text-olive-200',
            'fecha': c.fecha or _date.min, 'obj_id': c.id,
            'titulo': c.motivo_consulta or 'Consulta general',
            'detalles': detalles,
            'delete_url': _rev('delete_historia', kwargs={'id': c.id}),
            'edit_url': _rev('edit_historia', kwargs={'id': c.id}),
            'view_url': _rev('view_historia', kwargs={'id': c.id}),
            'download_url': None,
        })

    for v in vacunas:
        detalles = []
        if v.laboratorio: detalles.append(f"Lab: {v.laboratorio}")
        if v.dosis: detalles.append(f"Dosis: {v.dosis}")
        if v.proxima_dosis: detalles.append(f"Próx. dosis: {v.proxima_dosis}")
        tl.append({
            'tipo': 'Vacunación', 'icon': 'fa-syringe', 'badge': 'bg-green-800/80 text-green-200',
            'fecha': v.fecha or _date.min, 'obj_id': v.id,
            'titulo': v.nombre_vacuna or 'Vacuna',
            'detalles': detalles,
            'delete_url': _rev('delete_vacuna', kwargs={'id': v.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for d in desparasitaciones:
        detalles = []
        if d.tipo: detalles.append(d.tipo)
        if d.dosis: detalles.append(f"Dosis: {d.dosis}")
        if d.proxima_fecha: detalles.append(f"Próx: {d.proxima_fecha}")
        tl.append({
            'tipo': 'Desparasitación', 'icon': 'fa-bug', 'badge': 'bg-yellow-800/80 text-yellow-200',
            'fecha': d.fecha or _date.min, 'obj_id': d.id,
            'titulo': d.producto or 'Desparasitación',
            'detalles': detalles,
            'delete_url': _rev('delete_desparasitacion', kwargs={'id': d.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for r in recetas:
        detalles = []
        if r.diagnostico: detalles.append(f"Dx: {r.diagnostico[:80]}")
        meds = [it.medicamento for it in r.items.all()[:3]]
        if meds: detalles.append("Medicamentos: " + ", ".join(meds))
        tl.append({
            'tipo': 'Fórmula médica', 'icon': 'fa-prescription-bottle-medical', 'badge': 'bg-purple-800/80 text-purple-200',
            'fecha': r.fecha.date() if hasattr(r.fecha, 'date') else (_date.min), 'obj_id': r.id,
            'titulo': f"Receta #{r.numero}",
            'detalles': detalles,
            'delete_url': _rev('delete_receta', kwargs={'id': r.id}),
            'edit_url': None, 'view_url': _rev('view_receta', kwargs={'id': r.id}),
            'download_url': _rev('receta_pdf', kwargs={'id': r.id}),
        })

    for c in cirugias:
        detalles = []
        if c.preanestesico: detalles.append(f"Preanestésico: {c.preanestesico[:60]}")
        if c.complicaciones: detalles.append(f"Complicaciones: {c.complicaciones[:60]}")
        if c.veterinario: detalles.append(f"Dr. {_s(c.veterinario, 'nombre') or _s(c.veterinario, 'user')}")
        tl.append({
            'tipo': 'Cirugía', 'icon': 'fa-scalpel', 'badge': 'bg-red-800/80 text-red-200',
            'fecha': c.fecha or _date.min, 'obj_id': c.id,
            'titulo': c.nombre_cirugia or 'Cirugía',
            'detalles': detalles,
            'delete_url': _rev('delete_cirugia', kwargs={'id': c.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for e in examenes:
        detalles = []
        if e.laboratorio: detalles.append(f"Lab: {e.laboratorio}")
        if e.descripcion: detalles.append(e.descripcion[:80])
        if e.resultado: detalles.append(f"Resultado: {e.resultado[:60]}")
        tl.append({
            'tipo': 'Examen de laboratorio', 'icon': 'fa-microscope', 'badge': 'bg-cyan-800/80 text-cyan-200',
            'fecha': e.fecha or _date.min, 'obj_id': e.id,
            'titulo': e.get_tipo_examen_display() if hasattr(e, 'get_tipo_examen_display') else e.tipo_examen,
            'detalles': detalles,
            'delete_url': _rev('delete_examen', kwargs={'id': e.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for s in seguimientos:
        detalles = []
        if s.descripcion: detalles.append(s.descripcion[:80])
        if s.evolucion: detalles.append(f"Evolución: {s.evolucion[:60]}")
        if s.proximo_control: detalles.append(f"Próx. control: {s.proximo_control}")
        tl.append({
            'tipo': 'Seguimiento', 'icon': 'fa-chart-line', 'badge': 'bg-blue-800/80 text-blue-200',
            'fecha': s.fecha or _date.min, 'obj_id': s.id,
            'titulo': f"Seguimiento — {s.fecha}",
            'detalles': detalles,
            'delete_url': _rev('delete_seguimiento', kwargs={'id': s.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for o in ordenes:
        detalles = []
        if o.seleccion: detalles.append(o.seleccion)
        if o.prioridad: detalles.append(f"Prioridad: {o.prioridad}")
        if o.motivo: detalles.append(o.motivo[:60])
        tl.append({
            'tipo': 'Orden', 'icon': 'fa-file-prescription', 'badge': 'bg-indigo-800/80 text-indigo-200',
            'fecha': o.fecha or _date.min, 'obj_id': o.id,
            'titulo': o.tipo_orden or 'Orden',
            'detalles': detalles,
            'delete_url': _rev('delete_orden', kwargs={'id': o.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for img in imagenes:
        detalles = []
        if img.signos_clinicos: detalles.append(f"Signos: {img.signos_clinicos[:60]}")
        if img.diagnostico_presuntivo: detalles.append(f"Dx: {img.diagnostico_presuntivo[:60]}")
        if img.veterinario: detalles.append(f"Dr. {_s(img.veterinario, 'nombre') or _s(img.veterinario, 'user')}")
        tl.append({
            'tipo': 'Imagen diagnóstica', 'icon': 'fa-x-ray', 'badge': 'bg-pink-800/80 text-pink-200',
            'fecha': img.fecha or _date.min, 'obj_id': img.id,
            'titulo': img.ayuda_diagnostica or 'Imagen diagnóstica',
            'detalles': detalles,
            'delete_url': _rev('delete_imagen', kwargs={'id': img.id}),
            'edit_url': None, 'view_url': None,
            'download_url': img.adjunto.url if img.adjunto else None,
        })

    for doc in documentos:
        detalles = []
        if doc.tipo_documento: detalles.append(f"Tipo: {doc.tipo_documento}")
        if doc.requiere_firma == 'Si': detalles.append("Requiere firma")
        if doc.contenido: detalles.append(doc.contenido[:80])
        tl.append({
            'tipo': 'Documento', 'icon': 'fa-folder', 'badge': 'bg-orange-800/80 text-orange-200',
            'fecha': doc.fecha or _date.min, 'obj_id': doc.id,
            'titulo': doc.nombre_documento or 'Documento',
            'detalles': detalles,
            'delete_url': _rev('delete_documento', kwargs={'id': doc.id}),
            'edit_url': None, 'view_url': None,
            'download_url': _rev('descargar_documento', kwargs={'id': doc.id}),
        })

    for rem in remisiones:
        detalles = []
        if rem.motivo: detalles.append(rem.motivo[:80])
        if rem.diagnostico: detalles.append(f"Dx: {rem.diagnostico[:60]}")
        tl.append({
            'tipo': 'Remisión', 'icon': 'fa-share-from-square', 'badge': 'bg-teal-800/80 text-teal-200',
            'fecha': rem.fecha or _date.min, 'obj_id': rem.id,
            'titulo': f"Remisión a {rem.clinica_destino or 'clínica'}",
            'detalles': detalles,
            'delete_url': _rev('delete_remision', kwargs={'id': rem.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    for pel in peluquerias:
        detalles = []
        if pel.precio: detalles.append(f"Precio: ${pel.precio}")
        if pel.veterinario: detalles.append(f"Responsable: {_s(pel.veterinario, 'nombre') or _s(pel.veterinario, 'user')}")
        if pel.observaciones: detalles.append(pel.observaciones[:60])
        tl.append({
            'tipo': 'Peluquería y spa', 'icon': 'fa-scissors', 'badge': 'bg-rose-800/80 text-rose-200',
            'fecha': pel.fecha or _date.min, 'obj_id': pel.id,
            'titulo': pel.servicio or 'Servicio de peluquería',
            'detalles': detalles,
            'delete_url': _rev('delete_peluqueria', kwargs={'id': pel.id}),
            'edit_url': None, 'view_url': None, 'download_url': None,
        })

    tl.sort(key=lambda x: (x['fecha'], x['obj_id']), reverse=True)

    return render(request, "historia_paciente.html", {
        "mascota": _mascota_to_dict(m),
        "propietario": _prop_to_dict(m.propietario) if m.propietario else {},
        "tab": tab,
        "consultas": consultas,
        "vacunas": vacunas,
        "desparasitaciones": desparasitaciones,
        "recetas": recetas,
        "cirugias": cirugias,
        "examenes": examenes,
        "seguimientos": seguimientos,
        "citas": citas,
        "ordenes": ordenes,
        "imagenes": imagenes,
        "documentos": documentos,
        "remisiones": remisiones,
        "peluquerias": peluquerias,
        "vets": vets,
        "motivo_choices": HistoriaClinica.MOTIVO_CHOICES,
        "orden_prioridad_choices": Orden.PRIORIDAD_CHOICES,
        "peluqueria_servicio_choices": Peluqueria.SERVICIO_CHOICES,
        "total_consultas": len(consultas),
        "total_vacunas": len(vacunas),
        "total_desparasitaciones": len(desparasitaciones),
        "total_recetas": len(recetas),
        "total_cirugias": len(cirugias),
        "total_examenes": len(examenes),
        "total_seguimientos": len(seguimientos),
        "total_citas": len(citas),
        "total_ordenes": len(ordenes),
        "total_imagenes": len(imagenes),
        "total_documentos": len(documentos),
        "total_remisiones": len(remisiones),
        "total_peluquerias": len(peluquerias),
        "timeline": tl,
        "rol": request.session.get("rol"),
        "username": request.session.get("user"),
        "today": __import__('datetime').date.today().strftime("%Y-%m-%d"),
    })


# ─── Vacunas ───

def _parse_date(s):
    from datetime import datetime as dt
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@vet_or_admin_required
def add_vacuna(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        messages.error(request, "Mascota no encontrada.")
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=vacunas")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        Vacuna.objects.create(
            paciente=m,
            nombre_vacuna=(request.POST.get("nombre_vacuna") or "").strip(),
            fecha=fecha,
            laboratorio=(request.POST.get("laboratorio") or "").strip(),
            dosis=(request.POST.get("dosis") or "").strip(),
            lote=(request.POST.get("lote") or "").strip(),
            proxima_dosis=_parse_date(request.POST.get("proxima_dosis")),
            veterinario=vet,
            observaciones=(request.POST.get("observaciones") or "").strip(),
        )
        messages.success(request, "Vacuna registrada correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=vacunas")


@vet_or_admin_required
def delete_vacuna(request, id):
    v = Vacuna.objects.select_related("paciente").filter(pk=id).first()
    if v:
        pid = v.paciente_id
        v.delete()
        messages.info(request, "Vacuna eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=vacunas")
    return redirect("list_pacientes")


@vet_or_admin_required
def vacuna_pdf(request, id):
    """PDF de certificado individual de vacunación."""
    import io, os
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        Image as RLImage,
    )

    v = Vacuna.objects.select_related("paciente", "paciente__propietario", "veterinario").filter(pk=id).first()
    if not v:
        messages.error(request, "Vacuna no encontrada.")
        return redirect("list_pacientes")

    paciente   = v.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T",  parent=styles["Normal"], fontSize=13, fontName="Helvetica-Bold")
    sub_s   = ParagraphStyle("S",  parent=styles["Normal"], fontSize=9,  textColor=colors.HexColor("#444"))
    label_s = ParagraphStyle("L",  parent=styles["Normal"], fontSize=8,  fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#556B2F"))
    value_s = ParagraphStyle("V",  parent=styles["Normal"], fontSize=9)
    head_s  = ParagraphStyle("H",  parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#2d4a1e"))
    body_s  = ParagraphStyle("B",  parent=styles["Normal"], fontSize=9,  leading=13)

    biz_name    = getattr(settings, "BUSINESS_NAME",    "Kane Agropet")
    biz_nit     = getattr(settings, "BUSINESS_NIT",     "")
    biz_phone   = getattr(settings, "BUSINESS_PHONE",   "")
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

    fecha_str = v.fecha.strftime("%d/%m/%Y") if v.fecha else ""
    hdr_tbl = Table(
        [[logo_cell,
          Paragraph(biz_lines, title_s),
          Paragraph(f"<b>CERTIFICADO DE VACUNACIÓN</b><br/>Fecha: {fecha_str}", sub_s)]],
        colWidths=[3*cm, 9.5*cm, 5.5*cm]
    )
    hdr_tbl.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",       (2,0), (2, 0),  "RIGHT"),
        ("LINEBELOW",   (0,0), (-1,-1), 1, colors.HexColor("#556B2F")),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))

    story = [hdr_tbl, Spacer(1, 0.4*cm)]

    # Propietario
    prop_rows = [
        [Paragraph("<b>DATOS DEL PROPIETARIO</b>", head_s), "", "", ""],
        [Paragraph("Propietario:", label_s),
         Paragraph(propietario.nombre if propietario else "—", value_s),
         Paragraph("Documento:", label_s),
         Paragraph(f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—", value_s)],
        [Paragraph("Teléfono:", label_s),
         Paragraph(propietario.telefono if propietario else "—", value_s),
         Paragraph("Email:", label_s),
         Paragraph(propietario.email if propietario else "—", value_s)],
    ]
    pt = Table(prop_rows, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    pt.setStyle(TableStyle([
        ("SPAN",          (0,0), (-1,0)),
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#f0f4ea")),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [pt, Spacer(1, 0.3*cm)]

    # Paciente
    if paciente:
        from datetime import date as _d
        edad_str = ""
        if paciente.fecha_nacimiento:
            delta = _d.today() - paciente.fecha_nacimiento
            anos  = delta.days // 365
            meses = (delta.days % 365) // 30
            edad_str = f"{anos} año(s) {meses} mes(es)"

        pac_rows = [
            [Paragraph("<b>DATOS DEL PACIENTE</b>", head_s), "", "", ""],
            [Paragraph("Nombre:",  label_s), Paragraph(paciente.nombre  or "—", value_s),
             Paragraph("Especie:", label_s), Paragraph(paciente.especie or "—", value_s)],
            [Paragraph("Raza:",    label_s), Paragraph(paciente.raza    or "—", value_s),
             Paragraph("Sexo:",    label_s), Paragraph(paciente.sexo    or "—", value_s)],
            [Paragraph("Edad:",    label_s), Paragraph(edad_str         or "—", value_s),
             Paragraph("Chip:",    label_s), Paragraph(paciente.codigo_chip or "—", value_s)],
        ]
        pact = Table(pac_rows, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
        pact.setStyle(TableStyle([
            ("SPAN",          (0,0), (-1,0)),
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#f0f4ea")),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story += [pact, Spacer(1, 0.3*cm)]

    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#556B2F"), spaceAfter=0.3*cm))

    # Datos de la vacuna
    prox_str = v.proxima_dosis.strftime("%d/%m/%Y") if v.proxima_dosis else "—"
    vet_nombre = ""
    if v.veterinario:
        vet_nombre = v.veterinario.nombre or v.veterinario.user
        if v.veterinario.especialidad: vet_nombre += f" — {v.veterinario.especialidad}"
        if v.veterinario.license:      vet_nombre += f" | Lic: {v.veterinario.license}"

    vac_rows = [
        [Paragraph("<b>DATOS DE LA VACUNA</b>", head_s), "", "", ""],
        [Paragraph("Vacuna:",        label_s), Paragraph(v.nombre_vacuna or "—", value_s),
         Paragraph("Laboratorio:",   label_s), Paragraph(v.laboratorio   or "—", value_s)],
        [Paragraph("Fecha aplicación:", label_s), Paragraph(fecha_str or "—", value_s),
         Paragraph("Próxima dosis:",    label_s), Paragraph(prox_str, value_s)],
        [Paragraph("Dosis:",         label_s), Paragraph(v.dosis or "—", value_s),
         Paragraph("Lote:",          label_s), Paragraph(v.lote  or "—", value_s)],
        [Paragraph("Veterinario:",   label_s), Paragraph(vet_nombre or "—", value_s), "", ""],
    ]
    vt = Table(vac_rows, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    vt.setStyle(TableStyle([
        ("SPAN",          (0,0), (-1,0)),
        ("SPAN",          (1,4), (-1,4)),
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#e8f5e9")),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [vt, Spacer(1, 0.3*cm)]

    if v.observaciones:
        story.append(Paragraph("<b>Observaciones:</b>", label_s))
        story.append(Paragraph(v.observaciones, body_s))
        story.append(Spacer(1, 0.3*cm))

    # Firma
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width=6*cm, thickness=0.5, color=colors.HexColor("#999"), spaceAfter=0.1*cm))
    story.append(Paragraph("Firma y sello del veterinario", sub_s))

    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe_name = f"Vacuna_{v.nombre_vacuna.replace(' ','_')}_{paciente.nombre if paciente else 'Paciente'}.pdf"
    resp["Content-Disposition"] = f'inline; filename="{safe_name}"'
    return resp


# ─── Desparasitaciones ───

@vet_or_admin_required
def add_desparasitacion(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        messages.error(request, "Mascota no encontrada.")
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=desparasitaciones")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        Desparasitacion.objects.create(
            paciente=m,
            fecha=fecha,
            ultima_desparasitacion=_parse_date(request.POST.get("ultima_desparasitacion")),
            producto=(request.POST.get("producto") or "").strip(),
            tipo=(request.POST.get("tipo") or "Interna").strip(),
            dosis=(request.POST.get("dosis") or "").strip(),
            proxima_fecha=_parse_date(request.POST.get("proxima_fecha")),
            veterinario=vet,
            observaciones=(request.POST.get("observaciones") or "").strip(),
        )
        messages.success(request, "Desparasitación registrada correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=desparasitaciones")


@vet_or_admin_required
def delete_desparasitacion(request, id):
    d = Desparasitacion.objects.select_related("paciente").filter(pk=id).first()
    if d:
        pid = d.paciente_id
        d.delete()
        messages.info(request, "Desparasitación eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=desparasitaciones")
    return redirect("list_pacientes")


@vet_or_admin_required
def desparasitacion_pdf(request, id):
    """PDF de certificado individual de desparasitación."""
    import io, os
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        Image as RLImage,
    )

    d = Desparasitacion.objects.select_related("paciente", "paciente__propietario", "veterinario").filter(pk=id).first()
    if not d:
        messages.error(request, "Desparasitación no encontrada.")
        return redirect("list_pacientes")

    paciente    = d.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T",  parent=styles["Normal"], fontSize=13, fontName="Helvetica-Bold")
    sub_s   = ParagraphStyle("S",  parent=styles["Normal"], fontSize=9,  textColor=colors.HexColor("#444"))
    label_s = ParagraphStyle("L",  parent=styles["Normal"], fontSize=8,  fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#556B2F"))
    value_s = ParagraphStyle("V",  parent=styles["Normal"], fontSize=9)
    head_s  = ParagraphStyle("H",  parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#2d4a1e"))
    body_s  = ParagraphStyle("B",  parent=styles["Normal"], fontSize=9,  leading=13)

    biz_name    = getattr(settings, "BUSINESS_NAME",    "Kane Agropet")
    biz_nit     = getattr(settings, "BUSINESS_NIT",     "")
    biz_phone   = getattr(settings, "BUSINESS_PHONE",   "")
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

    fecha_str = d.fecha.strftime("%d/%m/%Y") if d.fecha else ""
    hdr_tbl = Table(
        [[logo_cell,
          Paragraph(biz_lines, title_s),
          Paragraph(f"<b>CERTIFICADO DE DESPARASITACIÓN</b><br/>Fecha: {fecha_str}", sub_s)]],
        colWidths=[3*cm, 9.5*cm, 5.5*cm]
    )
    hdr_tbl.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",       (2,0), (2, 0),  "RIGHT"),
        ("LINEBELOW",   (0,0), (-1,-1), 1, colors.HexColor("#556B2F")),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))

    story = [hdr_tbl, Spacer(1, 0.4*cm)]

    # Propietario
    prop_rows = [
        [Paragraph("<b>DATOS DEL PROPIETARIO</b>", head_s), "", "", ""],
        [Paragraph("Propietario:", label_s),
         Paragraph(propietario.nombre if propietario else "—", value_s),
         Paragraph("Documento:", label_s),
         Paragraph(f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—", value_s)],
        [Paragraph("Teléfono:", label_s),
         Paragraph(propietario.telefono if propietario else "—", value_s),
         Paragraph("Email:", label_s),
         Paragraph(propietario.email if propietario else "—", value_s)],
    ]
    pt = Table(prop_rows, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    pt.setStyle(TableStyle([
        ("SPAN",          (0,0), (-1,0)),
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#f0f4ea")),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [pt, Spacer(1, 0.3*cm)]

    # Paciente
    if paciente:
        from datetime import date as _d
        edad_str = ""
        if paciente.fecha_nacimiento:
            delta = _d.today() - paciente.fecha_nacimiento
            anos  = delta.days // 365
            meses = (delta.days % 365) // 30
            edad_str = f"{anos} año(s) {meses} mes(es)"

        pac_rows = [
            [Paragraph("<b>DATOS DEL PACIENTE</b>", head_s), "", "", ""],
            [Paragraph("Nombre:",  label_s), Paragraph(paciente.nombre  or "—", value_s),
             Paragraph("Especie:", label_s), Paragraph(paciente.especie or "—", value_s)],
            [Paragraph("Raza:",    label_s), Paragraph(paciente.raza    or "—", value_s),
             Paragraph("Sexo:",    label_s), Paragraph(paciente.sexo    or "—", value_s)],
            [Paragraph("Edad:",    label_s), Paragraph(edad_str         or "—", value_s),
             Paragraph("Chip:",    label_s), Paragraph(paciente.codigo_chip or "—", value_s)],
        ]
        pact = Table(pac_rows, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
        pact.setStyle(TableStyle([
            ("SPAN",          (0,0), (-1,0)),
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#f0f4ea")),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story += [pact, Spacer(1, 0.3*cm)]

    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#556B2F"), spaceAfter=0.3*cm))

    # Datos de la desparasitación
    ultima_str = d.ultima_desparasitacion.strftime("%d/%m/%Y") if d.ultima_desparasitacion else "—"
    prox_str   = d.proxima_fecha.strftime("%d/%m/%Y")          if d.proxima_fecha          else "—"
    vet_nombre = ""
    if d.veterinario:
        vet_nombre = d.veterinario.nombre or d.veterinario.user
        if d.veterinario.especialidad: vet_nombre += f" — {d.veterinario.especialidad}"
        if d.veterinario.license:      vet_nombre += f" | Lic: {d.veterinario.license}"

    des_rows = [
        [Paragraph("<b>DATOS DE LA DESPARASITACIÓN</b>", head_s), "", "", ""],
        [Paragraph("Producto:",          label_s), Paragraph(d.producto or "—", value_s),
         Paragraph("Tipo:",              label_s), Paragraph(d.tipo     or "—", value_s)],
        [Paragraph("Fecha aplicación:",  label_s), Paragraph(fecha_str or "—", value_s),
         Paragraph("Dosis:",             label_s), Paragraph(d.dosis    or "—", value_s)],
        [Paragraph("Últ. desparasitación:", label_s), Paragraph(ultima_str, value_s),
         Paragraph("Próxima fecha:",        label_s), Paragraph(prox_str,   value_s)],
        [Paragraph("Veterinario:",       label_s), Paragraph(vet_nombre or "—", value_s), "", ""],
    ]
    dt = Table(des_rows, colWidths=[3.5*cm, 6*cm, 3*cm, 5.5*cm])
    dt.setStyle(TableStyle([
        ("SPAN",          (0,0), (-1,0)),
        ("SPAN",          (1,4), (-1,4)),
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#e8f5e9")),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#ccc")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [dt, Spacer(1, 0.3*cm)]

    if d.observaciones:
        story.append(Paragraph("<b>Observaciones:</b>", label_s))
        story.append(Paragraph(d.observaciones, body_s))
        story.append(Spacer(1, 0.3*cm))

    # Firma
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width=6*cm, thickness=0.5, color=colors.HexColor("#999"), spaceAfter=0.1*cm))
    story.append(Paragraph("Firma y sello del veterinario", sub_s))

    doc.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe_name = f"Desparasitacion_{d.producto.replace(' ','_')}_{paciente.nombre if paciente else 'Paciente'}.pdf"
    resp["Content-Disposition"] = f'inline; filename="{safe_name}"'
    return resp


# ─── Cirugías ───

@vet_or_admin_required
def add_cirugia(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=cirugias")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        adjuntos_files = request.FILES.getlist("adjuntos[]")
        first_adj = adjuntos_files[0] if adjuntos_files else None
        cg = Cirugia.objects.create(
            paciente=m,
            fecha=fecha,
            nombre_cirugia=(request.POST.get("nombre_cirugia") or "").strip(),
            descripcion_quirurgica=(request.POST.get("descripcion_quirurgica") or "").strip(),
            preanestesico=(request.POST.get("preanestesico") or "").strip(),
            anestesico=(request.POST.get("anestesico") or "").strip(),
            otros_medicamentos=(request.POST.get("otros_medicamentos") or "").strip(),
            tratamiento=(request.POST.get("tratamiento") or "").strip(),
            observaciones=(request.POST.get("observaciones") or "").strip(),
            complicaciones=(request.POST.get("complicaciones") or "").strip(),
            adjunto=first_adj,
            veterinario=vet,
        )
        for f in adjuntos_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="cirugia", object_id=cg.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Cirugía/procedimiento registrado correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=cirugias")


@vet_or_admin_required
def delete_cirugia(request, id):
    c = Cirugia.objects.select_related("paciente").filter(pk=id).first()
    if c:
        pid = c.paciente_id
        c.delete()
        messages.info(request, "Cirugía eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=cirugias")
    return redirect("list_pacientes")


# ─── Exámenes de laboratorio ───

@vet_or_admin_required
def add_examen(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=diagnostico")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        adjunto_ex = request.FILES.get("adjunto_examen") or None
        extra_adj_ex = request.FILES.getlist("adjuntos[]")
        ex = ExamenLaboratorio.objects.create(
            paciente=m,
            fecha=fecha,
            tipo_examen=(request.POST.get("tipo_examen") or "Otro").strip(),
            descripcion=(request.POST.get("descripcion") or "").strip(),
            resultado=(request.POST.get("resultado") or "").strip(),
            laboratorio=(request.POST.get("laboratorio") or "").strip(),
            veterinario=vet,
            adjunto=adjunto_ex,
            observaciones=(request.POST.get("observaciones") or "").strip(),
        )
        for f in extra_adj_ex:
            if f:
                AdjuntoArchivo.objects.create(
                    tipo="examen", object_id=ex.id,
                    archivo=f, nombre_original=f.name,
                )
        messages.success(request, "Examen registrado correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=diagnostico")


@vet_or_admin_required
def delete_examen(request, id):
    e = ExamenLaboratorio.objects.select_related("paciente").filter(pk=id).first()
    if e:
        pid = e.paciente_id
        e.delete()
        messages.info(request, "Examen eliminado.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=diagnostico")
    return redirect("list_pacientes")


# ─── Seguimientos ───

@vet_or_admin_required
def add_seguimiento(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        # The form sends fecha_hora (datetime-local); extract date part
        fecha_raw = request.POST.get("fecha_hora") or request.POST.get("fecha") or ""
        fecha = _parse_date(fecha_raw.split("T")[0] if "T" in fecha_raw else fecha_raw)
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=seguimientos")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        # Support both single legacy field and new multi-file
        adjunto = request.FILES.get("adjunto_seguimiento") or None
        extra_adjuntos = request.FILES.getlist("adjuntos[]")

        sg = Seguimiento.objects.create(
            paciente=m,
            fecha=fecha,
            descripcion=(request.POST.get("descripcion") or "").strip(),
            evolucion=(request.POST.get("evolucion") or "").strip(),
            proximo_control=_parse_date(request.POST.get("proximo_control")),
            adjunto=adjunto,
            veterinario=vet,
        )
        for f in extra_adjuntos:
            if f:
                AdjuntoArchivo.objects.create(
                    tipo="seguimiento", object_id=sg.id,
                    archivo=f, nombre_original=f.name,
                )
        messages.success(request, "Seguimiento registrado correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=seguimientos")


@vet_or_admin_required
def delete_seguimiento(request, id):
    s = Seguimiento.objects.select_related("paciente").filter(pk=id).first()
    if s:
        pid = s.paciente_id
        s.delete()
        messages.info(request, "Seguimiento eliminado.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=seguimientos")
    return redirect("list_pacientes")


# ─── Fórmulas médicas (Recetas) desde historia ───

@vet_or_admin_required
def add_receta_historia(request, paciente_id):
    """Crea una receta desde la historia clínica del paciente."""
    from home.views.recetas import _next_numero
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha_str = (request.POST.get("fecha") or "").strip()
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        receta = Receta.objects.create(
            numero=_next_numero(),
            paciente=m,
            veterinario=vet,
            diagnostico=(request.POST.get("diagnostico") or "").strip(),
            indicaciones=(request.POST.get("indicaciones") or "").strip(),
            creado_por=current_user(request),
        )

        nombres = request.POST.getlist("medicamento[]")
        presentaciones = request.POST.getlist("presentacion[]")
        cantidades = request.POST.getlist("cantidad[]")
        posologias = request.POST.getlist("posologia[]")

        for i, nom in enumerate(nombres):
            if not nom.strip():
                continue
            RecetaItem.objects.create(
                receta=receta,
                medicamento=nom.strip(),
                presentacion=(presentaciones[i] if i < len(presentaciones) else ""),
                cantidad=(cantidades[i] if i < len(cantidades) else "1"),
                posologia=(posologias[i] if i < len(posologias) else ""),
            )

        messages.success(request, f"Fórmula médica #{receta.numero} registrada correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=recetas")


@vet_or_admin_required
def edit_receta_historia(request, id):
    """Edita una receta desde la historia clínica del paciente."""
    receta = Receta.objects.select_related("paciente").filter(pk=id).first()
    if not receta:
        messages.error(request, "Fórmula no encontrada.")
        return redirect("list_pacientes")
    pid = receta.paciente_id

    if request.method == "POST":
        fecha_str = (request.POST.get("fecha") or "").strip()
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        receta.veterinario = vet
        receta.diagnostico = (request.POST.get("diagnostico") or "").strip()
        receta.indicaciones = (request.POST.get("indicaciones") or "").strip()
        receta.save()

        # Reemplazar ítems
        receta.items.all().delete()
        nombres = request.POST.getlist("medicamento[]")
        presentaciones = request.POST.getlist("presentacion[]")
        cantidades = request.POST.getlist("cantidad[]")
        posologias = request.POST.getlist("posologia[]")

        for i, nom in enumerate(nombres):
            if not nom.strip():
                continue
            RecetaItem.objects.create(
                receta=receta,
                medicamento=nom.strip(),
                presentacion=(presentaciones[i] if i < len(presentaciones) else ""),
                cantidad=(cantidades[i] if i < len(cantidades) else "1"),
                posologia=(posologias[i] if i < len(posologias) else ""),
            )

        messages.success(request, "Fórmula médica actualizada correctamente.")

    return redirect(f"/patients/mascotas/{pid}/historia/?tab=recetas")


@vet_or_admin_required
def delete_desparasitacion(request, id):
    d = Desparasitacion.objects.select_related("paciente").filter(pk=id).first()
    if d:
        pid = d.paciente_id
        d.delete()
        messages.info(request, "Desparasitación eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=desparasitaciones")
    return redirect("list_pacientes")


# ─── Órdenes ───

@vet_or_admin_required
def add_orden(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=ordenes")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        Orden.objects.create(
            paciente=m,
            fecha=fecha,
            tipo_orden=(request.POST.get("tipo_orden") or "Otro").strip(),
            seleccion=(request.POST.get("seleccion") or "").strip(),
            cantidad=int(request.POST.get("cantidad") or 1),
            prioridad=(request.POST.get("prioridad") or "").strip(),
            notas=(request.POST.get("notas") or "").strip(),
            motivo=(request.POST.get("motivo") or "").strip(),
            veterinario=vet,
        )
        messages.success(request, "Orden registrada correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=ordenes")


@vet_or_admin_required
def delete_orden(request, id):
    obj = Orden.objects.select_related("paciente").filter(pk=id).first()
    if obj:
        pid = obj.paciente_id
        obj.delete()
        messages.info(request, "Orden eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=ordenes")
    return redirect("list_pacientes")


# ─── Imágenes diagnósticas ───

@vet_or_admin_required
def add_imagen(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=diagnostico")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        img = ImagenDiagnostica(
            paciente=m,
            fecha=fecha,
            ayuda_diagnostica=(request.POST.get("ayuda_diagnostica") or "Otro").strip(),
            veterinario=vet,
            signos_clinicos=(request.POST.get("signos_clinicos") or "").strip(),
            diagnostico_presuntivo=(request.POST.get("diagnostico_presuntivo") or "").strip(),
            tipo_estudio=(request.POST.get("tipo_estudio") or "").strip(),
            observaciones=(request.POST.get("observaciones") or "").strip(),
        )
        adjuntos_files = request.FILES.getlist("adjuntos[]")
        if adjuntos_files:
            img.adjunto = adjuntos_files[0]
        img.save()
        for f in adjuntos_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="imagen", object_id=img.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Imagen diagnóstica registrada correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=diagnostico")


@vet_or_admin_required
def delete_imagen(request, id):
    obj = ImagenDiagnostica.objects.select_related("paciente").filter(pk=id).first()
    if obj:
        pid = obj.paciente_id
        obj.delete()
        messages.info(request, "Imagen eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=diagnostico")
    return redirect("list_pacientes")


# ─── Documentos ───

@vet_or_admin_required
def add_documento(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=documentos")

        doc = Documento(
            paciente=m,
            fecha=fecha,
            tipo_documento=(request.POST.get("tipo_documento") or "").strip(),
            nombre_documento=(request.POST.get("nombre_documento") or "").strip(),
            requiere_firma=(request.POST.get("requiere_firma") or "No").strip(),
            contenido=(request.POST.get("contenido") or "").strip(),
        )
        adjuntos_files = request.FILES.getlist("adjuntos[]")
        if adjuntos_files:
            doc.adjunto = adjuntos_files[0]
        doc.save()
        for f in adjuntos_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="documento", object_id=doc.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Documento registrado correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=documentos")


@vet_or_admin_required
def delete_documento(request, id):
    obj = Documento.objects.select_related("paciente").filter(pk=id).first()
    if obj:
        pid = obj.paciente_id
        obj.delete()
        messages.info(request, "Documento eliminado.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=documentos")
    return redirect("list_pacientes")


# ─── Remisiones ───

@vet_or_admin_required
def add_remision(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=remisiones")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        Remision.objects.create(
            paciente=m,
            fecha=fecha,
            clinica_destino=(request.POST.get("clinica_destino") or "").strip(),
            motivo=(request.POST.get("motivo") or "").strip(),
            diagnostico=(request.POST.get("diagnostico") or "").strip(),
            observaciones=(request.POST.get("observaciones") or "").strip(),
            veterinario=vet,
        )
        messages.success(request, "Remisión registrada correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=remisiones")


@vet_or_admin_required
def delete_remision(request, id):
    obj = Remision.objects.select_related("paciente").filter(pk=id).first()
    if obj:
        pid = obj.paciente_id
        obj.delete()
        messages.info(request, "Remisión eliminada.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=remisiones")
    return redirect("list_pacientes")


# ─── Peluquería y spa ───

@vet_or_admin_required
def add_peluqueria(request, paciente_id):
    m = Paciente.objects.filter(pk=paciente_id).first()
    if not m:
        return redirect("list_pacientes")

    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=peluqueria")

        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None

        try:
            precio = float(request.POST.get("precio") or 0)
        except ValueError:
            precio = 0

        Peluqueria.objects.create(
            paciente=m,
            fecha=fecha,
            servicio=(request.POST.get("servicio") or "Baño").strip(),
            precio=precio,
            veterinario=vet,
            observaciones=(request.POST.get("observaciones") or "").strip(),
        )
        messages.success(request, "Servicio de peluquería registrado correctamente.")

    return redirect(f"/patients/mascotas/{paciente_id}/historia/?tab=peluqueria")


@vet_or_admin_required
def delete_peluqueria(request, id):
    obj = Peluqueria.objects.select_related("paciente").filter(pk=id).first()
    if obj:
        pid = obj.paciente_id
        obj.delete()
        messages.info(request, "Registro eliminado.")
        return redirect(f"/patients/mascotas/{pid}/historia/?tab=peluqueria")


# ─── PDF de Documento ─────────────────────────────────────────────────────────

@vet_or_admin_required
def descargar_documento(request, id):
    """Genera un PDF con encabezado clínico para un Documento de historia."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    doc_obj = Documento.objects.select_related("paciente", "paciente__propietario").filter(pk=id).first()
    if not doc_obj:
        messages.error(request, "Documento no encontrado.")
        return redirect("list_pacientes")

    paciente = doc_obj.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    centered = ParagraphStyle("centered", parent=styles["Normal"], alignment=TA_CENTER)
    bold_centered = ParagraphStyle("bold_centered", parent=centered, fontName="Helvetica-Bold")
    small_gray = ParagraphStyle("small_gray", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    small_gray_c = ParagraphStyle("small_gray_c", parent=small_gray, alignment=TA_CENTER)
    label_style = ParagraphStyle("label", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9)
    value_style = ParagraphStyle("value", parent=styles["Normal"], fontSize=9)
    section_title = ParagraphStyle("section_title", parent=styles["Normal"],
                                   fontName="Helvetica-Bold", fontSize=10,
                                   textColor=colors.HexColor("#3a6b35"))

    story = []

    # ── Encabezado ──────────────────────────────────────────────────────────
    biz_name = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit = getattr(settings, "BUSINESS_NIT", "")
    biz_phone = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")
    biz_email = getattr(settings, "BUSINESS_EMAIL", "")

    # Logo + datos clínica en tabla de 2 columnas
    logo_path = next((p for p in [os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"), os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg")] if os.path.exists(p)), "")
    logo_cell = ""
    if os.path.exists(logo_path):
        try:
            logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception:
            logo_cell = Paragraph("", styles["Normal"])

    clinic_info = [
        Paragraph(f"<b>{biz_name}</b>", bold_centered),
        Paragraph(biz_nit, small_gray_c) if biz_nit else Spacer(1, 0.1*cm),
        Paragraph(biz_address, small_gray_c) if biz_address else Spacer(1, 0.1*cm),
        Paragraph(f"{biz_phone}{' - ' + biz_email if biz_email else ''}", small_gray_c),
    ]

    doc_number = f"No. {doc_obj.id:07d}"
    doc_header_right = [
        Paragraph(f"<b>{doc_obj.tipo_documento or 'Documento'}</b>", bold_centered),
        Paragraph(doc_number, bold_centered),
        Paragraph(f"<font color='#3a6b35'>{doc_obj.fecha.strftime('%Y-%m-%d') if doc_obj.fecha else ''}</font>", centered),
    ]

    header_table = Table(
        [[logo_cell, clinic_info, doc_header_right]],
        colWidths=[3*cm, 11*cm, 4*cm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#3a6b35")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(header_table)

    # Subtítulo "Reservado al tratamiento de animales"
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<i>Reservado al tratamiento de animales</i>",
        ParagraphStyle("italic_center", parent=styles["Normal"],
                       alignment=TA_CENTER, fontSize=9, textColor=colors.grey)
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Datos del propietario ────────────────────────────────────────────────
    story.append(Paragraph("Datos del propietario", section_title))
    story.append(Spacer(1, 0.2*cm))

    prop_nombre = propietario.nombre if propietario else "—"
    prop_doc = f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—"
    prop_tel = propietario.telefono if propietario else "—"
    prop_dir = propietario.direccion if propietario else "—"

    prop_table = Table(
        [
            [Paragraph("<b>Nombre:</b>", label_style), Paragraph(prop_nombre, value_style),
             Paragraph("<b>Identificación:</b>", label_style), Paragraph(prop_doc, value_style),
             Paragraph("<b>Teléfono:</b>", label_style), Paragraph(prop_tel, value_style)],
            [Paragraph("<b>Dirección:</b>", label_style), Paragraph(prop_dir, value_style), "", "", "", ""],
        ],
        colWidths=[2.8*cm, 4*cm, 2.8*cm, 3*cm, 2*cm, 3.2*cm],
    )
    prop_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("SPAN", (1, 1), (5, 1)),
    ]))
    story.append(prop_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Datos del paciente ───────────────────────────────────────────────────
    pac_nombre = paciente.nombre if paciente else "—"
    pac_especie = paciente.especie if paciente else "—"
    pac_raza = paciente.raza if paciente else "—"
    pac_sexo = paciente.sexo if paciente else "—"
    pac_peso = f"{paciente.peso} {paciente.unidad_peso}" if paciente and paciente.peso else "—"

    story.append(Paragraph(f"🐾 Datos generales de <font color='#3a6b35'><b>{pac_nombre}</b></font>", section_title))
    story.append(Spacer(1, 0.2*cm))

    pac_table = Table(
        [
            [Paragraph("<b>Especie:</b>", label_style), Paragraph(pac_especie, value_style),
             Paragraph("<b>Raza:</b>", label_style), Paragraph(pac_raza, value_style),
             Paragraph("<b>Género:</b>", label_style), Paragraph(pac_sexo, value_style)],
            [Paragraph("<b>Peso:</b>", label_style), Paragraph(pac_peso, value_style),
             Paragraph("<b>Color:</b>", label_style), Paragraph(paciente.color if paciente else "—", value_style),
             "", ""],
        ],
        colWidths=[2.8*cm, 4*cm, 2.8*cm, 3*cm, 2*cm, 3.2*cm],
    )
    pac_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f5ee")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("SPAN", (4, 1), (5, 1)),
    ]))
    story.append(pac_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Contenido del documento ──────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#3a6b35")))
    story.append(Spacer(1, 0.3*cm))

    doc_nombre = doc_obj.nombre_documento or doc_obj.tipo_documento or "Documento"
    story.append(Paragraph(f"<b>{doc_nombre}</b>", ParagraphStyle(
        "doc_title", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER,
    )))
    story.append(Spacer(1, 0.4*cm))

    if doc_obj.contenido:
        for line in doc_obj.contenido.split("\n"):
            story.append(Paragraph(line or "&nbsp;", value_style))
            story.append(Spacer(1, 0.15*cm))

    # ── Adjunto embebido ─────────────────────────────────────────────────────
    if doc_obj.adjunto:
        adjunto_path = doc_obj.adjunto.path
        image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        if os.path.exists(adjunto_path) and adjunto_path.lower().endswith(image_exts):
            story.append(Spacer(1, 0.5*cm))
            story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#3a6b35")))
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph("<b>Archivo adjunto:</b>", label_style))
            story.append(Spacer(1, 0.2*cm))
            try:
                story.append(RLImage(adjunto_path, width=14*cm, height=10*cm, kind="proportional"))
            except Exception:
                story.append(Paragraph(f"[Adjunto: {os.path.basename(adjunto_path)}]", value_style))
        elif os.path.exists(adjunto_path):
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(f"<b>Adjunto:</b> {os.path.basename(adjunto_path)}", value_style))

    story.append(Spacer(1, 1.5*cm))

    # ── Firma del responsable ────────────────────────────────────────────────
    firma_name = request.session.get("user", "")
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black,
                            spaceAfter=0.1*cm, hAlign="LEFT"))
    story.append(Paragraph(f"<b>{firma_name}</b>", value_style))
    story.append(Paragraph("Responsable", small_gray))

    pdf.build(story)

    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe_name = (doc_obj.nombre_documento or "documento").replace(" ", "_")
    resp["Content-Disposition"] = f'inline; filename="{safe_name}_{doc_obj.id}.pdf"'
    return resp


# ─── PDF Imagen Diagnóstica ───────────────────────────────────────────────────

@vet_or_admin_required
def descargar_imagen(request, id):
    """Genera un PDF con encabezado clínico para una ImagenDiagnostica."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )

    img_obj = ImagenDiagnostica.objects.select_related(
        "paciente", "paciente__propietario", "veterinario"
    ).filter(pk=id).first()
    if not img_obj:
        messages.error(request, "Imagen no encontrada.")
        return redirect("list_pacientes")

    paciente    = img_obj.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    centered   = ParagraphStyle("c",  parent=styles["Normal"], alignment=TA_CENTER)
    bold_c     = ParagraphStyle("bc", parent=centered, fontName="Helvetica-Bold")
    small_c    = ParagraphStyle("sc", parent=styles["Normal"], fontSize=8,
                                textColor=colors.grey, alignment=TA_CENTER)
    label_s    = ParagraphStyle("lb", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9)
    value_s    = ParagraphStyle("vl", parent=styles["Normal"], fontSize=9)
    sec_title  = ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica-Bold",
                                fontSize=11, textColor=colors.HexColor("#3a6b35"))

    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────
    biz_name    = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit     = getattr(settings, "BUSINESS_NIT", "")
    biz_phone   = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")
    biz_email   = getattr(settings, "BUSINESS_EMAIL", "")

    logo_path = next((p for p in [os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"), os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg")] if os.path.exists(p)), "")
    logo_cell = Paragraph("", styles["Normal"])
    if os.path.exists(logo_path):
        try: logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception: pass

    clinic_lines = [
        Paragraph(f"<b>{biz_name}</b>", bold_c),
        Paragraph(biz_nit, small_c) if biz_nit else Spacer(1, 0.1*cm),
        Paragraph(biz_address, small_c) if biz_address else Spacer(1, 0.1*cm),
        Paragraph(f"{biz_phone}{' · ' + biz_email if biz_email else ''}", small_c),
    ]
    right_lines = [
        Paragraph(f"<b>{img_obj.ayuda_diagnostica or 'Imagen Diagnóstica'}</b>", bold_c),
        Paragraph(f"No. {img_obj.id:07d}", bold_c),
        Paragraph(f"<font color='#3a6b35'>{img_obj.fecha.strftime('%Y-%m-%d') if img_obj.fecha else ''}</font>", centered),
    ]
    hdr = Table([[logo_cell, clinic_lines, right_lines]], colWidths=[3*cm, 11*cm, 4*cm])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("LINEBELOW", (0,0), (-1,0), 1.5, colors.HexColor("#3a6b35")),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph("<i>Reservado al tratamiento de animales</i>",
                           ParagraphStyle("ic", parent=styles["Normal"], alignment=TA_CENTER,
                                          fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))

    # ── Propietario ────────────────────────────────────────────────────────
    story.append(Paragraph("Datos del propietario", sec_title))
    prop_nombre = propietario.nombre if propietario else "—"
    prop_doc    = f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—"
    prop_tel    = propietario.telefono if propietario else "—"
    prop_dir    = propietario.direccion if propietario else "—"
    prop_tbl = Table(
        [[Paragraph("<b>Nombre:</b>", label_s), Paragraph(prop_nombre, value_s),
          Paragraph("<b>Identificación:</b>", label_s), Paragraph(prop_doc, value_s),
          Paragraph("<b>Teléfono:</b>", label_s), Paragraph(prop_tel, value_s)],
         [Paragraph("<b>Dirección:</b>", label_s), Paragraph(prop_dir, value_s), "", "", "", ""]],
        colWidths=[2.8*cm, 4*cm, 2.8*cm, 3*cm, 2*cm, 3.2*cm],
    )
    prop_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"), ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f8faf6")), ("FONTSIZE",(0,0),(-1,-1),9),
        ("BOTTOMPADDING",(0,0),(-1,-1),4), ("TOPPADDING",(0,0),(-1,-1),4),
        ("SPAN",(1,1),(5,1)),
    ]))
    story.append(prop_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Paciente ───────────────────────────────────────────────────────────
    pac_nombre = paciente.nombre if paciente else "—"
    story.append(Paragraph(f"Datos de <font color='#3a6b35'><b>{pac_nombre}</b></font>", sec_title))
    pac_peso = f"{paciente.peso} {paciente.unidad_peso}" if paciente and paciente.peso else "—"
    pac_tbl = Table(
        [[Paragraph("<b>Especie:</b>", label_s), Paragraph(paciente.especie or "—", value_s),
          Paragraph("<b>Raza:</b>", label_s), Paragraph(paciente.raza or "—", value_s),
          Paragraph("<b>Género:</b>", label_s), Paragraph(paciente.sexo or "—", value_s)]],
        colWidths=[2.8*cm, 4*cm, 2.8*cm, 3*cm, 2*cm, 3.2*cm],
    )
    pac_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"), ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f0f5ee")), ("FONTSIZE",(0,0),(-1,-1),9),
        ("BOTTOMPADDING",(0,0),(-1,-1),4), ("TOPPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(pac_tbl)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3a6b35")))
    story.append(Spacer(1, 0.4*cm))

    # ── Contenido ──────────────────────────────────────────────────────────
    vet_name = (img_obj.veterinario.nombre or img_obj.veterinario.user) if img_obj.veterinario else "—"
    vet_lic_i = img_obj.veterinario.license if img_obj.veterinario and img_obj.veterinario.license else ""
    vet_esp_i = img_obj.veterinario.especialidad if img_obj.veterinario and img_obj.veterinario.especialidad else ""
    story.append(Paragraph(f"<b>{img_obj.ayuda_diagnostica or 'Imagen Diagnóstica'}</b>",
                           ParagraphStyle("title", parent=styles["Normal"], fontName="Helvetica-Bold",
                                          fontSize=13, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))

    detail_data = [
        [Paragraph("<b>Fecha:</b>", label_s), Paragraph(str(img_obj.fecha or "—"), value_s),
         Paragraph("<b>Profesional:</b>", label_s), Paragraph(vet_name, value_s)],
    ]
    if vet_lic_i or vet_esp_i:
        detail_data.append([
            Paragraph("<b>Especialidad:</b>", label_s), Paragraph(vet_esp_i or "—", value_s),
            Paragraph("<b>Lic. Profesional:</b>", label_s), Paragraph(vet_lic_i or "—", value_s),
        ])
    detail_tbl = Table(detail_data, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
    detail_tbl.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),9), ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
    ]))
    story.append(detail_tbl)
    story.append(Spacer(1, 0.3*cm))

    for label, val in [
        ("Signos clínicos", img_obj.signos_clinicos),
        ("Diagnóstico presuntivo", img_obj.diagnostico_presuntivo),
        ("Tipo de estudio", img_obj.tipo_estudio),
        ("Observaciones", img_obj.observaciones),
    ]:
        if val:
            story.append(Paragraph(f"<b>{label}:</b>", label_s))
            story.append(Paragraph(val, value_s))
            story.append(Spacer(1, 0.3*cm))

    # ── Adjunto embebido ─────────────────────────────────────────────────────
    if img_obj.adjunto:
        adjunto_path = img_obj.adjunto.path
        image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        if os.path.exists(adjunto_path) and adjunto_path.lower().endswith(image_exts):
            story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#3a6b35")))
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph("<b>Imagen adjunta:</b>", label_s))
            story.append(Spacer(1, 0.2*cm))
            try:
                story.append(RLImage(adjunto_path, width=14*cm, height=10*cm, kind="proportional"))
            except Exception:
                story.append(Paragraph(f"[Adjunto: {os.path.basename(adjunto_path)}]", value_s))
            story.append(Spacer(1, 0.3*cm))
        elif os.path.exists(adjunto_path):
            story.append(Paragraph(f"<b>Adjunto:</b> {os.path.basename(adjunto_path)}", value_s))

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black,
                            spaceAfter=0.1*cm, hAlign="LEFT"))
    story.append(Paragraph(f"<b>{vet_name}</b>", value_s))
    story.append(Paragraph("Responsable",
                           ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)))

    pdf.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe = (img_obj.ayuda_diagnostica or "imagen").replace(" ", "_")
    resp["Content-Disposition"] = f'inline; filename="{safe}_{img_obj.id}.pdf"'
    return resp


# ─── PDF Historia Clínica Completa ────────────────────────────────────────────

@vet_or_admin_required
def historia_pdf(request, paciente_id):
    """Genera PDF con todo el historial clínico del paciente, con encabezado Kane Agropet."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage, PageBreak,
    )

    paciente = Paciente.objects.select_related("propietario").filter(pk=paciente_id).first()
    if not paciente:
        messages.error(request, "Mascota no encontrada.")
        return redirect("list_pacientes")

    propietario = paciente.propietario

    # Filtro de fechas opcional
    from datetime import date as _date
    fecha_desde_str = request.GET.get("fecha_desde") or ""
    fecha_hasta_str = request.GET.get("fecha_hasta") or ""
    def _parse_range(s):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None
    fecha_desde = _parse_range(fecha_desde_str)
    fecha_hasta = _parse_range(fecha_hasta_str)

    def _qs_filter(qs):
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)
        return qs

    # Recopilar todos los registros
    consultas      = list(_qs_filter(HistoriaClinica.objects.filter(paciente=paciente)).order_by("fecha"))
    vacunas        = list(_qs_filter(Vacuna.objects.filter(paciente=paciente)).order_by("fecha"))
    desparas       = list(_qs_filter(Desparasitacion.objects.filter(paciente=paciente)).order_by("fecha"))
    recetas        = list(_qs_filter(Receta.objects.filter(paciente=paciente).select_related("veterinario").prefetch_related("items")).order_by("fecha"))
    cirugias       = list(_qs_filter(Cirugia.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))
    examenes       = list(_qs_filter(ExamenLaboratorio.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))
    seguimientos   = list(_qs_filter(Seguimiento.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))
    ordenes        = list(_qs_filter(Orden.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))
    imagenes       = list(_qs_filter(ImagenDiagnostica.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))
    documentos_qs  = list(_qs_filter(Documento.objects.filter(paciente=paciente)).order_by("fecha"))
    remisiones     = list(_qs_filter(Remision.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))
    peluquerias    = list(_qs_filter(Peluqueria.objects.filter(paciente=paciente).select_related("veterinario")).order_by("fecha"))

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    centered   = ParagraphStyle("c",  parent=styles["Normal"], alignment=TA_CENTER)
    bold_c     = ParagraphStyle("bc", parent=centered, fontName="Helvetica-Bold")
    small_gray = ParagraphStyle("sg", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    small_c    = ParagraphStyle("sc", parent=small_gray, alignment=TA_CENTER)
    label_s    = ParagraphStyle("lb", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9)
    value_s    = ParagraphStyle("vl", parent=styles["Normal"], fontSize=9)
    sec_title  = ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica-Bold",
                                fontSize=11, textColor=colors.HexColor("#3a6b35"),
                                spaceAfter=4)
    item_title = ParagraphStyle("it", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9,
                                textColor=colors.HexColor("#2d5a27"))
    body_s     = ParagraphStyle("bs", parent=styles["Normal"], fontSize=8, leading=12)

    def _s(v): return str(v) if v else "—"

    story = []

    # ── Encabezado ──────────────────────────────────────────────────────────
    biz_name    = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit     = getattr(settings, "BUSINESS_NIT", "")
    biz_phone   = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")
    biz_email   = getattr(settings, "BUSINESS_EMAIL", "")

    logo_path = next((p for p in [os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"), os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg")] if os.path.exists(p)), "")
    logo_cell = Paragraph("", styles["Normal"])
    if os.path.exists(logo_path):
        try:
            logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception:
            pass

    clinic_lines = [
        Paragraph(f"<b>{biz_name}</b>", bold_c),
        Paragraph(biz_nit, small_c) if biz_nit else Spacer(1, 0.1*cm),
        Paragraph(biz_address, small_c) if biz_address else Spacer(1, 0.1*cm),
        Paragraph(f"{biz_phone}{' · ' + biz_email if biz_email else ''}", small_c),
    ]
    right_lines = [
        Paragraph("<b>Historia Clínica</b>", bold_c),
        Paragraph(f"No. {paciente.id:07d}", bold_c),
        Paragraph(f"<font color='#3a6b35'>{__import__('datetime').date.today().strftime('%Y-%m-%d')}</font>", centered),
    ]
    header_tbl = Table([[logo_cell, clinic_lines, right_lines]], colWidths=[3*cm, 11*cm, 4*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#3a6b35")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph("<i>Reservado al tratamiento de animales</i>",
                           ParagraphStyle("italic_c", parent=styles["Normal"],
                                          alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))

    # ── Propietario ─────────────────────────────────────────────────────────
    story.append(Paragraph("Datos del propietario", sec_title))
    prop_nombre = propietario.nombre if propietario else "—"
    prop_doc    = f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—"
    prop_tel    = propietario.telefono if propietario else "—"
    prop_dir    = propietario.direccion if propietario else "—"
    prop_tbl = Table(
        [[Paragraph("<b>Nombre:</b>", label_s), Paragraph(prop_nombre, value_s),
          Paragraph("<b>Identificación:</b>", label_s), Paragraph(prop_doc, value_s),
          Paragraph("<b>Teléfono:</b>", label_s), Paragraph(prop_tel, value_s)],
         [Paragraph("<b>Dirección:</b>", label_s), Paragraph(prop_dir, value_s), "", "", "", ""]],
        colWidths=[2.8*cm, 4*cm, 2.8*cm, 3*cm, 2*cm, 3.2*cm],
    )
    prop_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f8faf6")),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("SPAN", (1,1), (5,1)),
    ]))
    story.append(prop_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Paciente ─────────────────────────────────────────────────────────────
    story.append(Paragraph(f"Datos de <font color='#3a6b35'><b>{paciente.nombre or 'Mascota'}</b></font>", sec_title))
    pac_peso = f"{paciente.peso} {paciente.unidad_peso}" if paciente.peso else "—"
    pac_tbl = Table(
        [[Paragraph("<b>Especie:</b>", label_s), Paragraph(_s(paciente.especie), value_s),
          Paragraph("<b>Raza:</b>", label_s), Paragraph(_s(paciente.raza), value_s),
          Paragraph("<b>Género:</b>", label_s), Paragraph(_s(paciente.sexo), value_s)],
         [Paragraph("<b>Peso:</b>", label_s), Paragraph(pac_peso, value_s),
          Paragraph("<b>Color:</b>", label_s), Paragraph(_s(paciente.color), value_s),
          Paragraph("<b>E. Reprod.:</b>", label_s), Paragraph(_s(paciente.estado_reproductivo), value_s)]],
        colWidths=[2.8*cm, 4*cm, 2.8*cm, 3*cm, 2*cm, 3.2*cm],
    )
    pac_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0f5ee")),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(pac_tbl)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3a6b35")))
    story.append(Spacer(1, 0.4*cm))

    # ── Helper para secciones ────────────────────────────────────────────────
    def _section(icon, title, items_list):
        if not items_list:
            return
        story.append(Paragraph(title, sec_title))
        story.append(Spacer(1, 0.2*cm))
        for row_data in items_list:
            story.append(Table(
                row_data,
                colWidths=[3*cm, 5*cm, 3*cm, 7*cm],
                style=TableStyle([
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                    ("FONTSIZE", (0,0), (-1,-1), 8),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                    ("TOPPADDING", (0,0), (-1,-1), 3),
                    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e8e8e8")),
                    ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f5f5f5")),
                ])
            ))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.3*cm))

    def _fmt_date(d):
        try:
            return d.strftime("%Y-%m-%d") if d else "—"
        except Exception:
            return "—"

    # ── Consultas ────────────────────────────────────────────────────────────
    if consultas:
        story.append(Paragraph("Consultas", sec_title))
        for c in consultas:
            rows = []
            if c.motivo_consulta: rows.append([Paragraph("<b>Motivo:</b>", label_s), Paragraph(c.motivo_consulta, body_s), "", ""])
            if c.subjetivo:       rows.append([Paragraph("<b>Subjetivo:</b>", label_s), Paragraph(c.subjetivo, body_s), "", ""])
            if c.objetivo:        rows.append([Paragraph("<b>Objetivo:</b>", label_s), Paragraph(c.objetivo, body_s), "", ""])
            if c.interpretacion:  rows.append([Paragraph("<b>Diagnóstico:</b>", label_s), Paragraph(c.interpretacion, body_s), "", ""])
            plan = getattr(c, 'plan_terapeutico', '') or getattr(c, 'plan', '') or ""
            if plan:              rows.append([Paragraph("<b>Plan:</b>", label_s), Paragraph(plan, body_s), "", ""])
            plan_dx = getattr(c, 'plan_diagnostico', '') or ""
            if plan_dx:           rows.append([Paragraph("<b>Plan dx:</b>", label_s), Paragraph(plan_dx, body_s), "", ""])
            vet_c = getattr(c, 'creado_por', None)
            vet_c_name = (vet_c.nombre or vet_c.user) if vet_c else "—"
            vet_c_lic = f" · Lic. Prof.: {vet_c.license}" if vet_c and vet_c.license else ""
            header_row = [[
                Paragraph(f"<b>Consulta #{c.hc_numero or c.id}</b> — {_fmt_date(c.fecha)} — {vet_c_name}{vet_c_lic}", item_title),
                Paragraph("", body_s), "", ""
            ]]
            tbl_data = header_row + rows if rows else header_row
            tbl = Table(tbl_data, colWidths=[4.5*cm, 7*cm, 0.1*cm, 6*cm])
            tbl.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e8e8e8")),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8f0e8")),
                ("SPAN", (0,0), (-1,0)),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ("TOPPADDING", (0,0), (-1,-1), 3),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 0.2*cm))
        story.append(Spacer(1, 0.3*cm))

    # ── Vacunas ──────────────────────────────────────────────────────────────
    if vacunas:
        story.append(Paragraph("Vacunaciones", sec_title))
        data_rows = [["Fecha", "Vacuna", "Laboratorio", "Dosis / Lote", "Próx. dosis", "Veterinario / Licencia"]]
        for v in vacunas:
            vet_v = getattr(v, 'veterinario', None)
            vet_v_str = f"{vet_v.nombre or vet_v.user}" + (f" (Lic: {vet_v.license})" if vet_v.license else "") if vet_v else "—"
            data_rows.append([
                _fmt_date(v.fecha), _s(v.nombre_vacuna),
                _s(getattr(v,'laboratorio','')),
                f"{_s(getattr(v,'dosis',''))} / {_s(getattr(v,'lote',''))}",
                _fmt_date(getattr(v,'proxima_dosis',None)),
                vet_v_str,
            ])
        t = Table(data_rows, colWidths=[2.5*cm, 4*cm, 3*cm, 3*cm, 2.5*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#3a6b35")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ── Desparasitaciones ────────────────────────────────────────────────────
    if desparas:
        story.append(Paragraph("Desparasitaciones", sec_title))
        data_rows = [["Fecha", "Producto", "Tipo", "Dosis", "Próxima", "Veterinario / Licencia"]]
        for d in desparas:
            vet_d = getattr(d, 'veterinario', None)
            vet_d_str = f"{vet_d.nombre or vet_d.user}" + (f" (Lic: {vet_d.license})" if vet_d.license else "") if vet_d else "—"
            data_rows.append([
                _fmt_date(d.fecha), _s(d.producto), _s(getattr(d,'tipo','')),
                _s(getattr(d,'dosis','')), _fmt_date(getattr(d,'proxima_fecha',None)), vet_d_str,
            ])
        t = Table(data_rows, colWidths=[2.5*cm, 3.5*cm, 2.5*cm, 2*cm, 2.5*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#3a6b35")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ── Recetas ──────────────────────────────────────────────────────────────
    if recetas:
        story.append(Paragraph("Formulas medicas", sec_title))
        for r in recetas:
            vet_name = (r.veterinario.nombre or r.veterinario.user) if r.veterinario else "—"
            vet_lic = f" · Lic. Prof.: {r.veterinario.license}" if r.veterinario and r.veterinario.license else ""
            story.append(Paragraph(f"<b>{r.numero}</b> — {_fmt_date(r.fecha)} — {vet_name}{vet_lic}", item_title))
            if r.diagnostico:
                story.append(Paragraph(f"Diagnóstico: {r.diagnostico}", body_s))
            med_rows = [["Medicamento", "Dosis", "Vía", "Frecuencia", "Duración"]]
            for it in r.items.all():
                med_rows.append([_s(it.medicamento), _s(it.dosis), _s(it.via), _s(it.frecuencia), _s(it.duracion)])
            mt = Table(med_rows, colWidths=[4*cm, 2.5*cm, 2*cm, 3*cm, 3*cm])
            mt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#5a8a50")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            story.append(mt)
            story.append(Spacer(1, 0.25*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Cirugías ─────────────────────────────────────────────────────────────
    if cirugias:
        story.append(Paragraph("Cirugias y procedimientos", sec_title))
        for c in cirugias:
            vet_name = (c.veterinario.nombre or c.veterinario.user) if getattr(c,'veterinario',None) else "—"
            vet_lic = f" · Lic. Prof.: {c.veterinario.license}" if getattr(c,'veterinario',None) and c.veterinario.license else ""
            lines = [f"<b>{_s(getattr(c,'nombre_cirugia',''))} — {_fmt_date(c.fecha)}</b> · {vet_name}{vet_lic}"]
            if getattr(c,'descripcion_quirurgica',''): lines.append(f"Desc. quirúrgica: {c.descripcion_quirurgica}")
            if getattr(c,'anestesico',''): lines.append(f"Anestésico: {c.anestesico}")
            if getattr(c,'otros_medicamentos',''): lines.append(f"Otros medicamentos: {c.otros_medicamentos}")
            if getattr(c,'tratamiento',''): lines.append(f"Tratamiento: {c.tratamiento}")
            if getattr(c,'observaciones',''): lines.append(f"Observaciones: {c.observaciones}")
            if getattr(c,'complicaciones',''): lines.append(f"Complicaciones: {c.complicaciones}")
            for ln in lines:
                story.append(Paragraph(ln, body_s))
            if c.adjunto and hasattr(c.adjunto, 'path') and os.path.exists(c.adjunto.path):
                _ext = os.path.splitext(c.adjunto.path)[1].lower()
                if _ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                    try:
                        story.append(Spacer(1, 0.1*cm))
                        story.append(RLImage(c.adjunto.path, width=8*cm, height=6*cm, kind='proportional'))
                    except Exception:
                        story.append(Paragraph(f"[Adjunto: {os.path.basename(c.adjunto.name)}]", body_s))
                else:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(c.adjunto.name)}]", body_s))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Exámenes ─────────────────────────────────────────────────────────────
    if examenes:
        story.append(Paragraph("Examenes de laboratorio", sec_title))
        for e in examenes:
            vet_name = (e.veterinario.nombre or e.veterinario.user) if getattr(e,'veterinario',None) else "—"
            vet_lic = f" · Lic. Prof.: {e.veterinario.license}" if getattr(e,'veterinario',None) and e.veterinario.license else ""
            story.append(Paragraph(f"<b>{_s(getattr(e,'tipo_examen',''))} — {_fmt_date(e.fecha)}</b> · {vet_name}{vet_lic}", item_title))
            if getattr(e,'descripcion',''): story.append(Paragraph(f"Descripción: {e.descripcion}", body_s))
            if getattr(e,'resultado',''): story.append(Paragraph(f"Resultado: {e.resultado}", body_s))
            if getattr(e,'laboratorio',''): story.append(Paragraph(f"Laboratorio: {e.laboratorio}", body_s))
            if getattr(e,'observaciones',''): story.append(Paragraph(f"Observaciones: {e.observaciones}", body_s))
            if e.adjunto and hasattr(e.adjunto, 'path') and os.path.exists(e.adjunto.path):
                _ext = os.path.splitext(e.adjunto.path)[1].lower()
                if _ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                    try:
                        story.append(Spacer(1, 0.1*cm))
                        story.append(RLImage(e.adjunto.path, width=8*cm, height=6*cm, kind='proportional'))
                    except Exception:
                        story.append(Paragraph(f"[Adjunto: {os.path.basename(e.adjunto.name)}]", body_s))
                else:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(e.adjunto.name)}]", body_s))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Seguimientos ─────────────────────────────────────────────────────────
    if seguimientos:
        story.append(Paragraph("Seguimientos", sec_title))
        for s in seguimientos:
            vet_name = (s.veterinario.nombre or s.veterinario.user) if getattr(s,'veterinario',None) else "—"
            vet_lic = f" · Lic. Prof.: {s.veterinario.license}" if getattr(s,'veterinario',None) and s.veterinario.license else ""
            story.append(Paragraph(f"<b>{_fmt_date(s.fecha)}</b> · {vet_name}{vet_lic}", item_title))
            if getattr(s,'descripcion',''): story.append(Paragraph(f"Descripción: {s.descripcion}", body_s))
            if getattr(s,'evolucion',''): story.append(Paragraph(f"Evolución: {s.evolucion}", body_s))
            if getattr(s,'proximo_control',None): story.append(Paragraph(f"Próximo control: {_fmt_date(s.proximo_control)}", body_s))
            if s.adjunto and hasattr(s.adjunto, 'path') and os.path.exists(s.adjunto.path):
                _ext = os.path.splitext(s.adjunto.path)[1].lower()
                if _ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                    try:
                        story.append(Spacer(1, 0.1*cm))
                        story.append(RLImage(s.adjunto.path, width=8*cm, height=6*cm, kind='proportional'))
                    except Exception:
                        story.append(Paragraph(f"[Adjunto: {os.path.basename(s.adjunto.name)}]", body_s))
                else:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(s.adjunto.name)}]", body_s))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Peluquería ────────────────────────────────────────────────────────────
    if peluquerias:
        story.append(Paragraph("Peluqueria y spa", sec_title))
        data_rows = [["Fecha", "Servicio", "Responsable", "Observaciones"]]
        for p in peluquerias:
            vet_name = (p.veterinario.nombre or p.veterinario.user) if getattr(p,'veterinario',None) else "—"
            data_rows.append([_fmt_date(p.fecha), _s(p.servicio), vet_name, _s(getattr(p,'observaciones',''))[:80]])
        t = Table(data_rows, colWidths=[3*cm, 4*cm, 4*cm, 7*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#3a6b35")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # ── Remisiones ────────────────────────────────────────────────────────────
    if remisiones:
        story.append(Paragraph("Remisiones", sec_title))
        for r in remisiones:
            vet_name = (r.veterinario.nombre or r.veterinario.user) if getattr(r,'veterinario',None) else "—"
            story.append(Paragraph(f"<b>{_fmt_date(r.fecha)}</b> → {_s(r.clinica_destino)} · {vet_name}", item_title))
            if r.motivo: story.append(Paragraph(f"Motivo: {r.motivo}", body_s))
            story.append(Spacer(1, 0.15*cm))

    # ── Órdenes ──────────────────────────────────────────────────────────────
    if ordenes:
        story.append(Paragraph("Órdenes médicas", sec_title))
        for o in ordenes:
            vet_name = (o.veterinario.nombre or o.veterinario.user) if getattr(o,'veterinario',None) else "—"
            vet_lic = f" · Lic. Prof.: {o.veterinario.license}" if getattr(o,'veterinario',None) and o.veterinario.license else ""
            story.append(Paragraph(f"<b>{_s(o.tipo_orden)} — {_fmt_date(o.fecha)}</b> · {vet_name}{vet_lic}", item_title))
            if o.seleccion: story.append(Paragraph(f"Selección: {o.seleccion}", body_s))
            if o.cantidad > 1: story.append(Paragraph(f"Cantidad: {o.cantidad}", body_s))
            if o.prioridad: story.append(Paragraph(f"Prioridad: {o.prioridad}", body_s))
            if o.motivo: story.append(Paragraph(f"Motivo: {o.motivo}", body_s))
            if o.notas: story.append(Paragraph(f"Notas: {o.notas}", body_s))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Imágenes diagnósticas ────────────────────────────────────────────────
    if imagenes:
        story.append(Paragraph("Imágenes diagnósticas", sec_title))
        for img in imagenes:
            vet_name = (img.veterinario.nombre or img.veterinario.user) if getattr(img,'veterinario',None) else "—"
            vet_lic = f" · Lic. Prof.: {img.veterinario.license}" if getattr(img,'veterinario',None) and img.veterinario.license else ""
            story.append(Paragraph(f"<b>{_s(img.ayuda_diagnostica)} — {_fmt_date(img.fecha)}</b> · {vet_name}{vet_lic}", item_title))
            if img.signos_clinicos: story.append(Paragraph(f"Signos clínicos: {img.signos_clinicos}", body_s))
            if img.diagnostico_presuntivo: story.append(Paragraph(f"Dx presuntivo: {img.diagnostico_presuntivo}", body_s))
            if img.tipo_estudio: story.append(Paragraph(f"Tipo de estudio: {img.tipo_estudio}", body_s))
            if img.observaciones: story.append(Paragraph(f"Observaciones: {img.observaciones}", body_s))
            if img.adjunto and hasattr(img.adjunto, 'path') and os.path.exists(img.adjunto.path):
                _ext = os.path.splitext(img.adjunto.path)[1].lower()
                if _ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                    try:
                        story.append(Spacer(1, 0.1*cm))
                        story.append(RLImage(img.adjunto.path, width=10*cm, height=8*cm, kind='proportional'))
                    except Exception:
                        story.append(Paragraph(f"[Imagen: {os.path.basename(img.adjunto.name)}]", body_s))
                else:
                    story.append(Paragraph(f"[Imagen: {os.path.basename(img.adjunto.name)}]", body_s))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Documentos ───────────────────────────────────────────────────────────
    if documentos_qs:
        story.append(Paragraph("Documentos", sec_title))
        for doc in documentos_qs:
            story.append(Paragraph(f"<b>{_s(doc.nombre_documento)}</b> — {_fmt_date(doc.fecha)} ({_s(doc.tipo_documento)})", item_title))
            if doc.contenido: story.append(Paragraph(doc.contenido, body_s))
            if doc.adjunto and hasattr(doc.adjunto, 'path') and os.path.exists(doc.adjunto.path):
                _ext = os.path.splitext(doc.adjunto.path)[1].lower()
                if _ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                    try:
                        story.append(Spacer(1, 0.1*cm))
                        story.append(RLImage(doc.adjunto.path, width=8*cm, height=6*cm, kind='proportional'))
                    except Exception:
                        story.append(Paragraph(f"[Adjunto: {os.path.basename(doc.adjunto.name)}]", body_s))
                else:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(doc.adjunto.name)}]", body_s))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # Si no hay ningún registro
    total = sum([len(consultas), len(vacunas), len(desparas), len(recetas),
                 len(cirugias), len(examenes), len(seguimientos),
                 len(peluquerias), len(remisiones), len(ordenes),
                 len(imagenes), len(documentos_qs)])
    if total == 0:
        story.append(Paragraph("Sin registros clínicos aún.", ParagraphStyle(
            "empty", parent=styles["Normal"], fontSize=10,
            textColor=colors.grey, alignment=TA_CENTER
        )))

    # ── Pie de página ────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Historia generada el {__import__('datetime').date.today().strftime('%Y-%m-%d')} — {biz_name}",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=7,
                       textColor=colors.grey, alignment=TA_CENTER)
    ))

    pdf.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe = (paciente.nombre or "historia").replace(" ", "_")
    resp["Content-Disposition"] = f'inline; filename="Historia_{safe}.pdf"'
    return resp


# ─── Edición de submódulos clínicos ──────────────────────────────────────────

@vet_or_admin_required
def edit_vacuna(request, id):
    v = Vacuna.objects.select_related("paciente").filter(pk=id).first()
    if not v:
        messages.error(request, "Vacuna no encontrada.")
        return redirect("list_pacientes")
    pid = v.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=vacunas")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        v.nombre_vacuna = (request.POST.get("nombre_vacuna") or "").strip()
        v.fecha = fecha
        v.laboratorio = (request.POST.get("laboratorio") or "").strip()
        v.dosis = (request.POST.get("dosis") or "").strip()
        v.lote = (request.POST.get("lote") or "").strip()
        v.proxima_dosis = _parse_date(request.POST.get("proxima_dosis"))
        v.veterinario = vet
        v.observaciones = (request.POST.get("observaciones") or "").strip()
        v.save()
        messages.success(request, "Vacuna actualizada.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=vacunas")


@vet_or_admin_required
def edit_desparasitacion(request, id):
    d = Desparasitacion.objects.select_related("paciente").filter(pk=id).first()
    if not d:
        messages.error(request, "Desparasitación no encontrada.")
        return redirect("list_pacientes")
    pid = d.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=desparasitaciones")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        d.producto = (request.POST.get("producto") or "").strip()
        d.tipo = (request.POST.get("tipo") or "Interna").strip()
        d.dosis = (request.POST.get("dosis") or "").strip()
        d.fecha = fecha
        d.ultima_desparasitacion = _parse_date(request.POST.get("ultima_desparasitacion"))
        d.proxima_fecha = _parse_date(request.POST.get("proxima_fecha"))
        d.veterinario = vet
        d.observaciones = (request.POST.get("observaciones") or "").strip()
        d.save()
        messages.success(request, "Desparasitación actualizada.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=desparasitaciones")


@vet_or_admin_required
def edit_cirugia(request, id):
    c = Cirugia.objects.select_related("paciente").filter(pk=id).first()
    if not c:
        messages.error(request, "Cirugía no encontrada.")
        return redirect("list_pacientes")
    pid = c.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=cirugias")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        c.fecha = fecha
        c.nombre_cirugia = (request.POST.get("nombre_cirugia") or "").strip()
        c.descripcion_quirurgica = (request.POST.get("descripcion_quirurgica") or "").strip()
        c.preanestesico = (request.POST.get("preanestesico") or "").strip()
        c.anestesico = (request.POST.get("anestesico") or "").strip()
        c.otros_medicamentos = (request.POST.get("otros_medicamentos") or "").strip()
        c.tratamiento = (request.POST.get("tratamiento") or "").strip()
        c.observaciones = (request.POST.get("observaciones") or "").strip()
        c.complicaciones = (request.POST.get("complicaciones") or "").strip()
        c.veterinario = vet
        adj_files = request.FILES.getlist("adjuntos[]")
        if adj_files:
            c.adjunto = adj_files[0]
        c.save()
        for f in adj_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="cirugia", object_id=c.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Cirugía actualizada.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=cirugias")


@vet_or_admin_required
def edit_examen(request, id):
    e = ExamenLaboratorio.objects.select_related("paciente").filter(pk=id).first()
    if not e:
        messages.error(request, "Examen no encontrado.")
        return redirect("list_pacientes")
    pid = e.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=diagnostico")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        e.fecha = fecha
        e.tipo_examen = (request.POST.get("tipo_examen") or "Otro").strip()
        e.descripcion = (request.POST.get("descripcion") or "").strip()
        e.resultado = (request.POST.get("resultado") or "").strip()
        e.laboratorio = (request.POST.get("laboratorio") or "").strip()
        e.observaciones = (request.POST.get("observaciones") or "").strip()
        e.veterinario = vet
        adj_files = request.FILES.getlist("adjuntos[]")
        if adj_files:
            e.adjunto = adj_files[0]
        e.save()
        for f in adj_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="examen", object_id=e.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Examen actualizado.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=diagnostico")


@vet_or_admin_required
def edit_seguimiento(request, id):
    s = Seguimiento.objects.select_related("paciente").filter(pk=id).first()
    if not s:
        messages.error(request, "Seguimiento no encontrado.")
        return redirect("list_pacientes")
    pid = s.paciente_id
    if request.method == "POST":
        fecha_raw = request.POST.get("fecha_hora") or request.POST.get("fecha") or ""
        fecha = _parse_date(fecha_raw.split("T")[0] if "T" in fecha_raw else fecha_raw)
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=seguimientos")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        s.fecha = fecha
        s.descripcion = (request.POST.get("descripcion") or "").strip()
        s.evolucion = (request.POST.get("evolucion") or "").strip()
        s.proximo_control = _parse_date(request.POST.get("proximo_control"))
        s.veterinario = vet
        adj_files = request.FILES.getlist("adjuntos[]")
        if adj_files:
            s.adjunto = adj_files[0]
        s.save()
        for f in adj_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="seguimiento", object_id=s.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Seguimiento actualizado.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=seguimientos")


@vet_or_admin_required
def edit_orden(request, id):
    o = Orden.objects.select_related("paciente").filter(pk=id).first()
    if not o:
        messages.error(request, "Orden no encontrada.")
        return redirect("list_pacientes")
    pid = o.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=ordenes")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        o.fecha = fecha
        o.tipo_orden = (request.POST.get("tipo_orden") or "Otro").strip()
        o.seleccion = (request.POST.get("seleccion") or "").strip()
        try:
            o.cantidad = int(request.POST.get("cantidad") or 1)
        except ValueError:
            o.cantidad = 1
        o.prioridad = (request.POST.get("prioridad") or "").strip()
        o.notas = (request.POST.get("notas") or "").strip()
        o.motivo = (request.POST.get("motivo") or "").strip()
        o.veterinario = vet
        o.save()
        messages.success(request, "Orden actualizada.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=ordenes")


@vet_or_admin_required
def edit_remision(request, id):
    r = Remision.objects.select_related("paciente").filter(pk=id).first()
    if not r:
        messages.error(request, "Remisión no encontrada.")
        return redirect("list_pacientes")
    pid = r.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=remisiones")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        r.fecha = fecha
        r.clinica_destino = (request.POST.get("clinica_destino") or "").strip()
        r.motivo = (request.POST.get("motivo") or "").strip()
        r.diagnostico = (request.POST.get("diagnostico") or "").strip()
        r.observaciones = (request.POST.get("observaciones") or "").strip()
        r.veterinario = vet
        r.save()
        messages.success(request, "Remisión actualizada.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=remisiones")


@vet_or_admin_required
def edit_peluqueria(request, id):
    p = Peluqueria.objects.select_related("paciente").filter(pk=id).first()
    if not p:
        messages.error(request, "Registro no encontrado.")
        return redirect("list_pacientes")
    pid = p.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=peluqueria")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        p.fecha = fecha
        p.servicio = (request.POST.get("servicio") or "Baño").strip()
        try:
            p.precio = float(request.POST.get("precio") or 0)
        except ValueError:
            p.precio = 0
        p.observaciones = (request.POST.get("observaciones") or "").strip()
        p.veterinario = vet
        p.save()
        messages.success(request, "Servicio actualizado.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=peluqueria")


# También necesitamos actualizar add_examen para manejar el adjunto:

@vet_or_admin_required
def _add_examen_with_adjunto(request, paciente_id):
    """Wrapper; la función real ya fue definida, este bloque actualiza add_examen inline."""
    pass  # No usar; reemplazado abajo.


# ─── PDF individual de cirugía ────────────────────────────────────────────────

@vet_or_admin_required
def cirugia_pdf(request, id):
    """Genera un PDF con encabezado clínico para una Cirugía."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )

    c_obj = Cirugia.objects.select_related(
        "paciente", "paciente__propietario", "veterinario"
    ).filter(pk=id).first()
    if not c_obj:
        messages.error(request, "Cirugía no encontrada.")
        return redirect("list_pacientes")

    paciente = c_obj.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    centered = ParagraphStyle("c", parent=styles["Normal"], alignment=TA_CENTER)
    bold_c = ParagraphStyle("bc", parent=centered, fontName="Helvetica-Bold")
    small_c = ParagraphStyle("sc", parent=styles["Normal"], fontSize=8,
                             textColor=colors.grey, alignment=TA_CENTER)
    label_s = ParagraphStyle("lb", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9)
    value_s = ParagraphStyle("vl", parent=styles["Normal"], fontSize=9)
    sec_title = ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica-Bold",
                               fontSize=11, textColor=colors.HexColor("#3a6b35"))

    story = []

    biz_name = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit = getattr(settings, "BUSINESS_NIT", "")
    biz_phone = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")
    biz_email = getattr(settings, "BUSINESS_EMAIL", "")

    logo_path = next((p for p in [os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"), os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg")] if os.path.exists(p)), "")
    logo_cell = Paragraph("", styles["Normal"])
    if os.path.exists(logo_path):
        try:
            logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception:
            pass

    clinic_lines = [
        Paragraph(f"<b>{biz_name}</b>", bold_c),
        Paragraph(biz_nit, small_c) if biz_nit else Spacer(1, 0.1*cm),
        Paragraph(biz_address, small_c) if biz_address else Spacer(1, 0.1*cm),
        Paragraph(f"{biz_phone}{' · ' + biz_email if biz_email else ''}", small_c),
    ]
    right_lines = [
        Paragraph("<b>Reporte de Cirugía</b>", bold_c),
        Paragraph(f"No. {c_obj.id:07d}", bold_c),
        Paragraph(f"<font color='#3a6b35'>{c_obj.fecha.strftime('%Y-%m-%d') if c_obj.fecha else ''}</font>", centered),
    ]
    hdr = Table([[logo_cell, clinic_lines, right_lines]], colWidths=[3*cm, 11*cm, 4*cm])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#3a6b35")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph("<i>Reservado al tratamiento de animales</i>",
                           ParagraphStyle("ic", parent=styles["Normal"],
                                          alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))

    # Propietario
    story.append(Paragraph("Datos del propietario", sec_title))
    story.append(Spacer(1, 0.15*cm))
    prop_nombre = propietario.nombre if propietario else "—"
    prop_doc = f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—"
    prop_tel = propietario.telefono if propietario else "—"
    prop_dir = propietario.direccion if propietario else "—"
    prop_tbl = Table(
        [[Paragraph("<b>Nombre:</b>", label_s), Paragraph(prop_nombre, value_s),
          Paragraph("<b>ID:</b>", label_s), Paragraph(prop_doc, value_s),
          Paragraph("<b>Tel:</b>", label_s), Paragraph(prop_tel, value_s)],
         [Paragraph("<b>Dirección:</b>", label_s), Paragraph(prop_dir, value_s), "", "", "", ""]],
        colWidths=[2.5*cm, 4.5*cm, 1.5*cm, 4*cm, 1.5*cm, 3.8*cm],
    )
    prop_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("SPAN", (1, 1), (5, 1)),
    ]))
    story.append(prop_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Paciente
    story.append(Paragraph(f"Datos de <font color='#3a6b35'><b>{paciente.nombre or 'Paciente'}</b></font>", sec_title))
    story.append(Spacer(1, 0.15*cm))
    pac_peso = f"{paciente.peso} {paciente.unidad_peso}" if paciente and paciente.peso else "—"
    pac_tbl = Table(
        [[Paragraph("<b>Especie:</b>", label_s), Paragraph(paciente.especie or "—", value_s),
          Paragraph("<b>Raza:</b>", label_s), Paragraph(paciente.raza or "—", value_s),
          Paragraph("<b>Peso:</b>", label_s), Paragraph(pac_peso, value_s)]],
        colWidths=[2.5*cm, 4.5*cm, 1.5*cm, 4*cm, 1.5*cm, 3.8*cm],
    )
    pac_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f5ee")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(pac_tbl)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3a6b35")))
    story.append(Spacer(1, 0.4*cm))

    # Datos de la cirugía
    vet_name = (c_obj.veterinario.nombre or c_obj.veterinario.user) if c_obj.veterinario else "—"
    vet_lic = c_obj.veterinario.license if c_obj.veterinario and c_obj.veterinario.license else ""
    vet_esp = c_obj.veterinario.especialidad if c_obj.veterinario and c_obj.veterinario.especialidad else ""
    story.append(Paragraph(f"<b>{c_obj.nombre_cirugia}</b>",
                           ParagraphStyle("title2", parent=styles["Normal"],
                                          fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))

    detail_rows = [
        [Paragraph("<b>Fecha:</b>", label_s), Paragraph(str(c_obj.fecha or "—"), value_s),
         Paragraph("<b>Veterinario:</b>", label_s), Paragraph(vet_name, value_s)],
    ]
    if vet_esp or vet_lic:
        detail_rows.append([
            Paragraph("<b>Especialidad:</b>", label_s), Paragraph(vet_esp or "—", value_s),
            Paragraph("<b>Lic. Profesional:</b>", label_s), Paragraph(vet_lic or "—", value_s),
        ])
    if c_obj.preanestesico or c_obj.anestesico:
        detail_rows.append([
            Paragraph("<b>Preanestésico:</b>", label_s), Paragraph(c_obj.preanestesico or "—", value_s),
            Paragraph("<b>Anestésico:</b>", label_s), Paragraph(c_obj.anestesico or "—", value_s),
        ])
    detail_tbl = Table(detail_rows, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    detail_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
    ]))
    story.append(detail_tbl)
    story.append(Spacer(1, 0.3*cm))

    for label, val in [
        ("Descripción quirúrgica", c_obj.descripcion_quirurgica),
        ("Otros medicamentos", c_obj.otros_medicamentos),
        ("Tratamiento", c_obj.tratamiento),
        ("Observaciones", c_obj.observaciones),
        ("Complicaciones", c_obj.complicaciones),
    ]:
        if val:
            story.append(Paragraph(f"<b>{label}:</b>", label_s))
            story.append(Paragraph(val, value_s))
            story.append(Spacer(1, 0.3*cm))

    # Adjuntos embebidos (campo único + AdjuntoArchivo múltiples)
    image_exts_c = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    all_adjuntos_c = []
    if c_obj.adjunto:
        all_adjuntos_c.append(c_obj.adjunto.path)
    for adj in AdjuntoArchivo.objects.filter(tipo="cirugia", object_id=c_obj.id):
        try:
            all_adjuntos_c.append(adj.archivo.path)
        except Exception:
            pass
    if all_adjuntos_c:
        story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#3a6b35")))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("<b>Archivos adjuntos:</b>", label_s))
        story.append(Spacer(1, 0.2*cm))
        for adjunto_path in all_adjuntos_c:
            if os.path.exists(adjunto_path) and adjunto_path.lower().endswith(image_exts_c):
                try:
                    story.append(RLImage(adjunto_path, width=14*cm, height=10*cm, kind="proportional"))
                    story.append(Spacer(1, 0.2*cm))
                except Exception:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(adjunto_path)}]", value_s))
            elif os.path.exists(adjunto_path):
                story.append(Paragraph(f"Adjunto: {os.path.basename(adjunto_path)}", value_s))

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black,
                            spaceAfter=0.1*cm, hAlign="LEFT"))
    story.append(Paragraph(f"<b>{vet_name}</b>", value_s))
    story.append(Paragraph("Veterinario responsable",
                           ParagraphStyle("small", parent=styles["Normal"],
                                          fontSize=8, textColor=colors.grey)))

    pdf.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe = (c_obj.nombre_cirugia or "cirugia").replace(" ", "_")
    resp["Content-Disposition"] = f'inline; filename="{safe}_{c_obj.id}.pdf"'
    return resp


# ─── PDF individual de examen ──────────────────────────────────────────────────

@vet_or_admin_required
def examen_pdf(request, id):
    """Genera un PDF con encabezado clínico para un ExamenLaboratorio."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )

    e_obj = ExamenLaboratorio.objects.select_related(
        "paciente", "paciente__propietario", "veterinario"
    ).filter(pk=id).first()
    if not e_obj:
        messages.error(request, "Examen no encontrado.")
        return redirect("list_pacientes")

    paciente = e_obj.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    centered = ParagraphStyle("c", parent=styles["Normal"], alignment=TA_CENTER)
    bold_c = ParagraphStyle("bc", parent=centered, fontName="Helvetica-Bold")
    small_c = ParagraphStyle("sc", parent=styles["Normal"], fontSize=8,
                             textColor=colors.grey, alignment=TA_CENTER)
    label_s = ParagraphStyle("lb", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9)
    value_s = ParagraphStyle("vl", parent=styles["Normal"], fontSize=9)
    sec_title = ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica-Bold",
                               fontSize=11, textColor=colors.HexColor("#3a6b35"))

    story = []

    biz_name = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit = getattr(settings, "BUSINESS_NIT", "")
    biz_phone = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")
    biz_email = getattr(settings, "BUSINESS_EMAIL", "")

    logo_path = next((p for p in [os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"), os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg")] if os.path.exists(p)), "")
    logo_cell = Paragraph("", styles["Normal"])
    if os.path.exists(logo_path):
        try:
            logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception:
            pass

    clinic_lines = [
        Paragraph(f"<b>{biz_name}</b>", bold_c),
        Paragraph(biz_nit, small_c) if biz_nit else Spacer(1, 0.1*cm),
        Paragraph(biz_address, small_c) if biz_address else Spacer(1, 0.1*cm),
        Paragraph(f"{biz_phone}{' · ' + biz_email if biz_email else ''}", small_c),
    ]
    right_lines = [
        Paragraph("<b>Examen de Laboratorio</b>", bold_c),
        Paragraph(f"No. {e_obj.id:07d}", bold_c),
        Paragraph(f"<font color='#3a6b35'>{e_obj.fecha.strftime('%Y-%m-%d') if e_obj.fecha else ''}</font>", centered),
    ]
    hdr = Table([[logo_cell, clinic_lines, right_lines]], colWidths=[3*cm, 11*cm, 4*cm])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#3a6b35")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph("<i>Reservado al tratamiento de animales</i>",
                           ParagraphStyle("ic", parent=styles["Normal"],
                                          alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))

    # Propietario + Paciente
    story.append(Paragraph("Propietario", sec_title))
    story.append(Spacer(1, 0.15*cm))
    prop_nombre = propietario.nombre if propietario else "—"
    prop_doc = f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—"
    prop_tel = propietario.telefono if propietario else "—"
    prop_tbl = Table(
        [[Paragraph("<b>Nombre:</b>", label_s), Paragraph(prop_nombre, value_s),
          Paragraph("<b>ID:</b>", label_s), Paragraph(prop_doc, value_s),
          Paragraph("<b>Tel:</b>", label_s), Paragraph(prop_tel, value_s)]],
        colWidths=[2.5*cm, 4.5*cm, 1.5*cm, 4*cm, 1.5*cm, 3.8*cm],
    )
    prop_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(prop_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"🐾 Paciente: <font color='#3a6b35'><b>{paciente.nombre or '—'}</b></font> — {paciente.especie or ''} / {paciente.raza or ''}", sec_title))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3a6b35")))
    story.append(Spacer(1, 0.4*cm))

    vet_name = (e_obj.veterinario.nombre or e_obj.veterinario.user) if e_obj.veterinario else "—"
    vet_lic_e = e_obj.veterinario.license if e_obj.veterinario and e_obj.veterinario.license else ""
    vet_esp_e = e_obj.veterinario.especialidad if e_obj.veterinario and e_obj.veterinario.especialidad else ""
    tipo_display = e_obj.tipo_examen or "Examen"
    story.append(Paragraph(f"<b>{tipo_display}</b>",
                           ParagraphStyle("title3", parent=styles["Normal"],
                                          fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))

    detail_rows_e = [
        [Paragraph("<b>Fecha:</b>", label_s), Paragraph(str(e_obj.fecha or "—"), value_s),
         Paragraph("<b>Laboratorio:</b>", label_s), Paragraph(e_obj.laboratorio or "—", value_s),
         Paragraph("<b>Profesional:</b>", label_s), Paragraph(vet_name, value_s)],
    ]
    if vet_lic_e or vet_esp_e:
        detail_rows_e.append([
            Paragraph("<b>Especialidad:</b>", label_s), Paragraph(vet_esp_e or "—", value_s),
            Paragraph("<b>Lic. Profesional:</b>", label_s), Paragraph(vet_lic_e or "—", value_s),
            "", "",
        ])
    detail_tbl = Table(detail_rows_e, colWidths=[2.5*cm, 3.5*cm, 2.5*cm, 3.5*cm, 2.8*cm, 3*cm],
    )
    detail_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
    ]))
    story.append(detail_tbl)
    story.append(Spacer(1, 0.3*cm))

    for label, val in [
        ("Descripción / Orden", e_obj.descripcion),
        ("Resultado", e_obj.resultado),
        ("Observaciones", e_obj.observaciones),
    ]:
        if val:
            story.append(Paragraph(f"<b>{label}:</b>", label_s))
            story.append(Paragraph(val, value_s))
            story.append(Spacer(1, 0.3*cm))

    # Adjuntos embebidos (campo único + AdjuntoArchivo múltiples)
    image_exts_e = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    all_adjuntos_e = []
    if e_obj.adjunto:
        all_adjuntos_e.append(e_obj.adjunto.path)
    for adj in AdjuntoArchivo.objects.filter(tipo="examen", object_id=e_obj.id):
        try:
            all_adjuntos_e.append(adj.archivo.path)
        except Exception:
            pass
    if all_adjuntos_e:
        story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#3a6b35")))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("<b>Archivos adjuntos:</b>", label_s))
        story.append(Spacer(1, 0.2*cm))
        for adjunto_path in all_adjuntos_e:
            if os.path.exists(adjunto_path) and adjunto_path.lower().endswith(image_exts_e):
                try:
                    story.append(RLImage(adjunto_path, width=14*cm, height=10*cm, kind="proportional"))
                    story.append(Spacer(1, 0.2*cm))
                except Exception:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(adjunto_path)}]", value_s))
            elif os.path.exists(adjunto_path):
                story.append(Paragraph(f"Adjunto: {os.path.basename(adjunto_path)}", value_s))

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black,
                            spaceAfter=0.1*cm, hAlign="LEFT"))
    story.append(Paragraph(f"<b>{vet_name}</b>", value_s))
    story.append(Paragraph("Veterinario responsable",
                           ParagraphStyle("small2", parent=styles["Normal"],
                                          fontSize=8, textColor=colors.grey)))

    pdf.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    safe = (tipo_display or "examen").replace(" ", "_")
    resp["Content-Disposition"] = f'inline; filename="{safe}_{e_obj.id}.pdf"'
    return resp


# ─── Edit imagen diagnóstica ──────────────────────────────────────────────────

@vet_or_admin_required
def edit_imagen(request, id):
    img = ImagenDiagnostica.objects.select_related("paciente").filter(pk=id).first()
    if not img:
        messages.error(request, "Imagen no encontrada.")
        return redirect("list_pacientes")
    pid = img.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=diagnostico")
        vet_id = request.POST.get("veterinario_id") or None
        vet = Usuario.objects.filter(pk=vet_id).first() if vet_id else None
        img.fecha = fecha
        img.ayuda_diagnostica = (request.POST.get("ayuda_diagnostica") or "Otro").strip()
        img.signos_clinicos = (request.POST.get("signos_clinicos") or "").strip()
        img.diagnostico_presuntivo = (request.POST.get("diagnostico_presuntivo") or "").strip()
        img.tipo_estudio = (request.POST.get("tipo_estudio") or "").strip()
        img.observaciones = (request.POST.get("observaciones") or "").strip()
        img.veterinario = vet
        adj_files = request.FILES.getlist("adjuntos[]")
        if adj_files:
            img.adjunto = adj_files[0]
        img.save()
        for f in adj_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="imagen", object_id=img.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Imagen actualizada.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=diagnostico")


# ─── Edit documento ────────────────────────────────────────────────────────────

@vet_or_admin_required
def edit_documento(request, id):
    doc = Documento.objects.select_related("paciente").filter(pk=id).first()
    if not doc:
        messages.error(request, "Documento no encontrado.")
        return redirect("list_pacientes")
    pid = doc.paciente_id
    if request.method == "POST":
        fecha = _parse_date(request.POST.get("fecha"))
        if not fecha:
            messages.error(request, "La fecha es requerida.")
            return redirect(f"/patients/mascotas/{pid}/historia/?tab=documentos")
        doc.fecha = fecha
        doc.tipo_documento = (request.POST.get("tipo_documento") or "").strip()
        doc.nombre_documento = (request.POST.get("nombre_documento") or "").strip()
        doc.requiere_firma = (request.POST.get("requiere_firma") or "No").strip()
        doc.contenido = (request.POST.get("contenido") or "").strip()
        adj_files = request.FILES.getlist("adjuntos[]")
        if adj_files:
            doc.adjunto = adj_files[0]
        doc.save()
        for f in adj_files[1:]:
            if f:
                AdjuntoArchivo.objects.create(tipo="documento", object_id=doc.id, archivo=f, nombre_original=f.name)
        messages.success(request, "Documento actualizado.")
    return redirect(f"/patients/mascotas/{pid}/historia/?tab=documentos")


# ─── PDF de seguimiento ────────────────────────────────────────────────────────

@vet_or_admin_required
def seguimiento_pdf(request, id):
    """Genera un PDF con encabezado clínico para un Seguimiento."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage,
    )

    s_obj = Seguimiento.objects.select_related(
        "paciente", "paciente__propietario", "veterinario"
    ).filter(pk=id).first()
    if not s_obj:
        messages.error(request, "Seguimiento no encontrado.")
        return redirect("list_pacientes")

    paciente = s_obj.paciente
    propietario = paciente.propietario if paciente else None

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    centered = ParagraphStyle("c", parent=styles["Normal"], alignment=TA_CENTER)
    bold_c = ParagraphStyle("bc", parent=centered, fontName="Helvetica-Bold")
    small_c = ParagraphStyle("sc", parent=styles["Normal"], fontSize=8,
                             textColor=colors.grey, alignment=TA_CENTER)
    label_s = ParagraphStyle("lb", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9)
    value_s = ParagraphStyle("vl", parent=styles["Normal"], fontSize=9)
    sec_title = ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica-Bold",
                               fontSize=11, textColor=colors.HexColor("#3a6b35"))

    story = []

    biz_name = getattr(settings, "BUSINESS_NAME", "Kane Agropet")
    biz_nit = getattr(settings, "BUSINESS_NIT", "")
    biz_phone = getattr(settings, "BUSINESS_PHONE", "")
    biz_address = getattr(settings, "BUSINESS_ADDRESS", "")
    biz_email = getattr(settings, "BUSINESS_EMAIL", "")

    logo_path = next((p for p in [os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.png"), os.path.join(settings.BASE_DIR, "home", "static", "LogoKane.jpeg")] if os.path.exists(p)), "")
    logo_cell = Paragraph("", styles["Normal"])
    if os.path.exists(logo_path):
        try:
            logo_cell = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
        except Exception:
            pass

    clinic_lines = [
        Paragraph(f"<b>{biz_name}</b>", bold_c),
        Paragraph(biz_nit, small_c) if biz_nit else Spacer(1, 0.1*cm),
        Paragraph(biz_address, small_c) if biz_address else Spacer(1, 0.1*cm),
        Paragraph(f"{biz_phone}{' · ' + biz_email if biz_email else ''}", small_c),
    ]
    right_lines = [
        Paragraph("<b>Reporte de Seguimiento</b>", bold_c),
        Paragraph(f"No. {s_obj.id:07d}", bold_c),
        Paragraph(f"<font color='#3a6b35'>{s_obj.fecha.strftime('%Y-%m-%d') if s_obj.fecha else ''}</font>", centered),
    ]
    hdr = Table([[logo_cell, clinic_lines, right_lines]], colWidths=[3*cm, 11*cm, 4*cm])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#3a6b35")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.25*cm))
    story.append(Paragraph("<i>Reservado al tratamiento de animales</i>",
                           ParagraphStyle("ic", parent=styles["Normal"],
                                          alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 0.4*cm))

    # Propietario
    story.append(Paragraph("Propietario", sec_title))
    story.append(Spacer(1, 0.15*cm))
    prop_nombre = propietario.nombre if propietario else "—"
    prop_doc = f"{propietario.tipo_documento}: {propietario.numero_documento}" if propietario and propietario.numero_documento else "—"
    prop_tel = propietario.telefono if propietario else "—"
    prop_tbl = Table(
        [[Paragraph("<b>Nombre:</b>", label_s), Paragraph(prop_nombre, value_s),
          Paragraph("<b>ID:</b>", label_s), Paragraph(prop_doc, value_s),
          Paragraph("<b>Tel:</b>", label_s), Paragraph(prop_tel, value_s)]],
        colWidths=[2.5*cm, 4.5*cm, 1.5*cm, 4*cm, 1.5*cm, 3.8*cm],
    )
    prop_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(prop_tbl)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Paciente: <font color='#3a6b35'><b>{paciente.nombre or '—'}</b></font> — {paciente.especie or ''} / {paciente.raza or ''}",
        sec_title))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3a6b35")))
    story.append(Spacer(1, 0.4*cm))

    vet_name = (s_obj.veterinario.nombre or s_obj.veterinario.user) if s_obj.veterinario else "—"
    vet_lic_s = s_obj.veterinario.license if s_obj.veterinario and s_obj.veterinario.license else ""
    vet_esp_s = s_obj.veterinario.especialidad if s_obj.veterinario and s_obj.veterinario.especialidad else ""
    story.append(Paragraph("<b>Seguimiento Clínico</b>",
                           ParagraphStyle("title3", parent=styles["Normal"],
                                          fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))

    detail_rows_s = [
        [Paragraph("<b>Fecha:</b>", label_s), Paragraph(str(s_obj.fecha or "—"), value_s),
         Paragraph("<b>Próx. control:</b>", label_s), Paragraph(str(s_obj.proximo_control or "—"), value_s),
         Paragraph("<b>Veterinario:</b>", label_s), Paragraph(vet_name, value_s)],
    ]
    if vet_lic_s or vet_esp_s:
        detail_rows_s.append([
            Paragraph("<b>Especialidad:</b>", label_s), Paragraph(vet_esp_s or "—", value_s),
            Paragraph("<b>Lic. Profesional:</b>", label_s), Paragraph(vet_lic_s or "—", value_s),
            "", "",
        ])
    detail_tbl = Table(detail_rows_s, colWidths=[2.5*cm, 3.5*cm, 2.5*cm, 3.5*cm, 2.8*cm, 3*cm],
    )
    detail_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faf6")),
    ]))
    story.append(detail_tbl)
    story.append(Spacer(1, 0.3*cm))

    for label, val in [
        ("Descripción / Detalles", s_obj.descripcion),
        ("Evolución", s_obj.evolucion),
    ]:
        if val:
            story.append(Paragraph(f"<b>{label}:</b>", label_s))
            story.append(Paragraph(val, value_s))
            story.append(Spacer(1, 0.3*cm))

    # Adjuntos (campo único + AdjuntoArchivo múltiples)
    image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    all_adjuntos = []
    if hasattr(s_obj, 'adjunto') and s_obj.adjunto:
        all_adjuntos.append(s_obj.adjunto.path)
    for adj in AdjuntoArchivo.objects.filter(tipo="seguimiento", object_id=s_obj.id):
        try:
            all_adjuntos.append(adj.archivo.path)
        except Exception:
            pass
    if all_adjuntos:
        story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#3a6b35")))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("<b>Archivos adjuntos:</b>", label_s))
        story.append(Spacer(1, 0.2*cm))
        for adjunto_path in all_adjuntos:
            if os.path.exists(adjunto_path) and adjunto_path.lower().endswith(image_exts):
                try:
                    story.append(RLImage(adjunto_path, width=14*cm, height=10*cm, kind="proportional"))
                    story.append(Spacer(1, 0.2*cm))
                except Exception:
                    story.append(Paragraph(f"[Adjunto: {os.path.basename(adjunto_path)}]", value_s))
            elif os.path.exists(adjunto_path):
                story.append(Paragraph(f"Adjunto: {os.path.basename(adjunto_path)}", value_s))

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width=8*cm, thickness=0.5, color=colors.black,
                            spaceAfter=0.1*cm, hAlign="LEFT"))
    story.append(Paragraph(f"<b>{vet_name}</b>", value_s))
    story.append(Paragraph("Veterinario responsable",
                           ParagraphStyle("small3", parent=styles["Normal"],
                                          fontSize=8, textColor=colors.grey)))

    pdf.build(story)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="seguimiento_{s_obj.id}.pdf"'
    return resp
