from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("reports/", views.reports, name="reports"),

    # Auth (admin only — no public register)
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("edit/", views.edit_profile, name="edit_profile"),

    # Pacientes / Propietarios
    path("patients/", views.list_propietarios, name="list_pacientes"),
    path("patients/add/", views.add_propietario, name="add_paciente"),
    path("patients/<str:id>/edit/", views.edit_propietario, name="edit_propietario"),
    path("patients/<str:id>/delete/", views.delete_propietario, name="delete_propietario"),
    path("patients/<str:propietario_id>/mascotas/", views.mascotas_propietario, name="mascotas_propietario"),
    path("patients/<str:propietario_id>/mascotas/add/", views.add_mascota, name="add_mascota"),
    path("patients/mascotas/<str:id>/edit/", views.edit_mascota, name="edit_mascota"),
    path("patients/mascotas/<str:id>/delete/", views.delete_mascota, name="delete_mascota"),
    path("patients/mascotas/<str:paciente_id>/historia/", views.historia_paciente, name="historia_paciente"),
    path("patients/mascotas/<str:paciente_id>/historia/pdf/", views.historia_pdf, name="historia_pdf"),
    path("patients/mascotas/<str:paciente_id>/historia/vacunas/add/", views.add_vacuna, name="add_vacuna"),
    path("patients/vacunas/<str:id>/delete/", views.delete_vacuna, name="delete_vacuna"),
    path("patients/mascotas/<str:paciente_id>/historia/desparasitaciones/add/", views.add_desparasitacion, name="add_desparasitacion"),
    path("patients/desparasitaciones/<str:id>/delete/", views.delete_desparasitacion, name="delete_desparasitacion"),
    path("patients/mascotas/<str:paciente_id>/historia/cirugias/add/", views.add_cirugia, name="add_cirugia"),
    path("patients/cirugias/<str:id>/delete/", views.delete_cirugia, name="delete_cirugia"),
    path("patients/mascotas/<str:paciente_id>/historia/examenes/add/", views.add_examen, name="add_examen"),
    path("patients/examenes/<str:id>/delete/", views.delete_examen, name="delete_examen"),
    path("patients/mascotas/<str:paciente_id>/historia/seguimientos/add/", views.add_seguimiento, name="add_seguimiento"),
    path("patients/seguimientos/<str:id>/delete/", views.delete_seguimiento, name="delete_seguimiento"),
    path("patients/mascotas/<str:paciente_id>/historia/receta/add/", views.add_receta_historia, name="add_receta_historia"),
    path("patients/recetas/<str:id>/edit/", views.edit_receta_historia, name="edit_receta_historia"),
    path("patients/mascotas/<str:paciente_id>/historia/ordenes/add/", views.add_orden, name="add_orden"),
    path("patients/ordenes/<str:id>/delete/", views.delete_orden, name="delete_orden"),
    path("patients/mascotas/<str:paciente_id>/historia/imagenes/add/", views.add_imagen, name="add_imagen"),
    path("patients/imagenes/<str:id>/delete/", views.delete_imagen, name="delete_imagen"),
    path("patients/imagenes/<str:id>/pdf/", views.descargar_imagen, name="descargar_imagen"),
    path("patients/mascotas/<str:paciente_id>/historia/documentos/add/", views.add_documento, name="add_documento"),
    path("patients/documentos/<str:id>/delete/", views.delete_documento, name="delete_documento"),
    path("patients/documentos/<str:id>/pdf/", views.descargar_documento, name="descargar_documento"),
    path("patients/mascotas/<str:paciente_id>/historia/remisiones/add/", views.add_remision, name="add_remision"),
    path("patients/remisiones/<str:id>/delete/", views.delete_remision, name="delete_remision"),
    path("patients/mascotas/<str:paciente_id>/historia/peluqueria/add/", views.add_peluqueria, name="add_peluqueria"),
    path("patients/peluqueria/<str:id>/delete/", views.delete_peluqueria, name="delete_peluqueria"),
    # Edit submodules
    path("patients/vacunas/<str:id>/edit/", views.edit_vacuna, name="edit_vacuna"),
    path("patients/desparasitaciones/<str:id>/edit/", views.edit_desparasitacion, name="edit_desparasitacion"),
    path("patients/cirugias/<str:id>/edit/", views.edit_cirugia, name="edit_cirugia"),
    path("patients/examenes/<str:id>/edit/", views.edit_examen, name="edit_examen"),
    path("patients/seguimientos/<str:id>/edit/", views.edit_seguimiento, name="edit_seguimiento"),
    path("patients/ordenes/<str:id>/edit/", views.edit_orden, name="edit_orden"),
    path("patients/remisiones/<str:id>/edit/", views.edit_remision, name="edit_remision"),
    path("patients/peluqueria/<str:id>/edit/", views.edit_peluqueria, name="edit_peluqueria"),
    # PDF submodules
    path("patients/vacunas/<str:id>/pdf/", views.vacuna_pdf, name="vacuna_pdf"),
    path("patients/desparasitaciones/<str:id>/pdf/", views.desparasitacion_pdf, name="desparasitacion_pdf"),
    path("patients/cirugias/<str:id>/pdf/", views.cirugia_pdf, name="cirugia_pdf"),
    path("patients/examenes/<str:id>/pdf/", views.examen_pdf, name="examen_pdf"),
    path("patients/imagenes/<str:id>/edit/", views.edit_imagen, name="edit_imagen"),
    path("patients/documentos/<str:id>/edit/", views.edit_documento, name="edit_documento"),
    path("patients/seguimientos/<str:id>/pdf/", views.seguimiento_pdf, name="seguimiento_pdf"),
    path("patients/consultas/<str:id>/pdf/", views.consulta_pdf, name="consulta_pdf"),
    # Legacy Pacientes CRUD (redirects via views)
    path("patients/legacy/edit/<str:id>/", views.edit_paciente, name="edit_paciente"),
    path("patients/legacy/delete/<str:id>/", views.delete_paciente, name="delete_paciente"),

    # Veterinarios CRUD
    path("vets/", views.list_veterinarios, name="list_veterinarios"),
    path("vets/add/", views.add_veterinario, name="add_veterinario"),
    path("vets/edit/<str:id>/", views.edit_veterinario, name="edit_veterinario"),
    path("vets/delete/<str:id>/", views.delete_veterinario, name="delete_veterinario"),

    # Citas CRUD (one-step booking, no payment)
    path("appointments/", views.list_citas, name="list_citas"),
    path("appointments/add/", views.add_cita, name="add_cita"),
    path("appointments/api/month/", views.citas_por_mes, name="citas_por_mes"),
    path("appointments/edit/<str:id>/", views.edit_cita, name="edit_cita"),
    path("citas/cancel/<str:id>/", views.cancel_cita, name="cancel_cita"),
    path("citas/add-observation/<str:id>/", views.add_observation, name="add_observation"),
    # Tarifas de citas
    path("citas/tarifas/", views.list_tarifas, name="list_tarifas"),
    path("citas/tarifas/add/", views.add_tarifa, name="add_tarifa"),
    path("citas/tarifas/<str:id>/edit/", views.edit_tarifa, name="edit_tarifa"),
    path("citas/tarifas/<str:id>/delete/", views.delete_tarifa, name="delete_tarifa"),

    # Admin user management
    path("panel/users/", views.admin_users_list, name="admin_users_list"),
    path("panel/users/add/", views.admin_users_add, name="admin_users_add"),
    path("panel/users/edit/<str:id>/", views.admin_users_edit, name="admin_users_edit"),
    path("panel/users/delete/<str:id>/", views.admin_users_delete, name="admin_users_delete"),
    path("panel/users/reset/<str:id>/", views.admin_users_reset_password, name="admin_users_reset_password"),

    # Medical histories
    path("historias/", views.list_historias, name="list_historias"),
    path("historias/view/<str:id>/", views.view_historia, name="view_historia"),
    path("historias/add/", views.add_historia, name="add_historia"),
    path("historias/edit/<str:id>/", views.edit_historia, name="edit_historia"),
    path("historias/delete/<str:id>/", views.delete_historia, name="delete_historia"),

    # Inventario - categorías
    path("categorias/", views.list_categorias, name="list_categorias"),
    path("categorias/add/", views.add_categoria, name="add_categoria"),
    path("categorias/edit/<str:id>/", views.edit_categoria, name="edit_categoria"),
    path("categorias/delete/<str:id>/", views.delete_categoria, name="delete_categoria"),

    # Inventario - productos
    path("productos/", views.list_productos, name="list_productos"),
    path("productos/add/", views.add_producto, name="add_producto"),
    path("productos/edit/<str:id>/", views.edit_producto, name="edit_producto"),
    path("productos/delete/<str:id>/", views.delete_producto, name="delete_producto"),
    path("productos/<str:producto_id>/movimientos/", views.list_movimientos, name="list_movimientos"),
    path("productos/<str:producto_id>/entrada/", views.add_entrada, name="add_entrada"),
    path("productos/<str:producto_id>/salida/", views.add_salida, name="add_salida"),
    path("productos/<str:producto_id>/descuento/", views.toggle_descuento, name="toggle_descuento"),
    path("movimientos/<int:mov_id>/pdf/", views.entrada_pdf, name="entrada_pdf"),
    path("productos/<str:producto_id>/historial-pdf/", views.historial_precios_pdf, name="historial_precios_pdf"),

    # Ventas
    path("ventas/", views.list_ventas, name="list_ventas"),
    path("ventas/add/", views.add_venta, name="add_venta"),
    path("ventas/view/<str:id>/", views.view_venta, name="view_venta"),
    path("ventas/edit/<str:id>/", views.edit_venta, name="edit_venta"),
    path("ventas/delete/<str:id>/", views.delete_venta, name="delete_venta"),
    path("ventas/cancel/<str:id>/", views.cancel_venta, name="cancel_venta"),
    path("ventas/<str:id>/invoice.pdf", views.invoice_pdf, name="invoice_pdf"),
    path("ventas/<str:id>/resend/", views.resend_invoice, name="resend_invoice"),
    path("ventas/<str:id>/email/", views.send_invoice_email, name="send_invoice_email"),

    # Recetario
    path("recetas/", views.list_recetas, name="list_recetas"),
    path("recetas/add/", views.add_receta, name="add_receta"),
    path("recetas/view/<str:id>/", views.view_receta, name="view_receta"),
    path("recetas/delete/<str:id>/", views.delete_receta, name="delete_receta"),
    path("recetas/<str:id>/pdf", views.receta_pdf, name="receta_pdf"),
]
