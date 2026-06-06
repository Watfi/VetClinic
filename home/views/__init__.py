"""View package — admin-only ORM views (vetclinic desktop)."""

from .auth import login, logout, edit_profile  # noqa: F401
from .dashboard import index, reports  # noqa: F401
from .pacientes import (  # noqa: F401
    list_pacientes, add_paciente, edit_paciente, delete_paciente,
)
from .propietarios import (  # noqa: F401
    list_propietarios, add_propietario, edit_propietario, delete_propietario,
    mascotas_propietario, add_mascota, edit_mascota, delete_mascota,
    historia_paciente, add_vacuna, delete_vacuna,
    add_desparasitacion, delete_desparasitacion,
    add_cirugia, delete_cirugia,
    add_examen, delete_examen,
    add_seguimiento, delete_seguimiento,
    add_receta_historia, edit_receta_historia,
    add_orden, delete_orden,
    add_imagen, delete_imagen,
    add_documento, delete_documento,
    add_remision, delete_remision,
    add_peluqueria, delete_peluqueria,
    descargar_documento,
    descargar_imagen,
    historia_pdf,
    # Edit views
    edit_vacuna, edit_desparasitacion, edit_cirugia, edit_examen,
    edit_seguimiento, edit_orden, edit_remision, edit_peluqueria,
    # PDF views
    cirugia_pdf, examen_pdf, seguimiento_pdf, vacuna_pdf, desparasitacion_pdf,
    # Additional edit views
    edit_imagen, edit_documento,
)
from .veterinarios import (  # noqa: F401
    list_veterinarios, add_veterinario, edit_veterinario, delete_veterinario,
)
from .citas import (  # noqa: F401
    list_citas, add_cita, edit_cita, cancel_cita, add_observation,
    citas_por_mes,
)
from .historias import (  # noqa: F401
    list_historias, view_historia, add_historia, edit_historia, delete_historia,
    consulta_pdf,
)
from .admin_panel import (  # noqa: F401
    admin_users_list, admin_users_add, admin_users_edit,
    admin_users_delete, admin_users_reset_password,
)
from .inventario import (  # noqa: F401
    list_categorias, add_categoria, edit_categoria, delete_categoria,
    list_productos, add_producto, edit_producto, delete_producto,
    list_movimientos, add_entrada, add_salida, toggle_descuento, entrada_pdf, historial_precios_pdf,
)
from .ventas import (  # noqa: F401
    list_ventas, add_venta, view_venta, edit_venta, delete_venta,
    cancel_venta, invoice_pdf, resend_invoice,
    send_invoice_email,
)
from .recetas import (  # noqa: F401
    list_recetas, add_receta, view_receta, delete_receta, receta_pdf,
)
from .tarifas import (  # noqa: F401
    list_tarifas, add_tarifa, edit_tarifa, delete_tarifa,
)
