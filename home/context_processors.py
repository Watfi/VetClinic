from django.conf import settings
from home.models import Usuario


def user_context(request):
    rol = request.session.get("rol")
    username = request.session.get("user")

    # Compute modulos_acceso for sidebar and template checks
    modulos_acceso = []
    if rol == Usuario.ROL_SUPERADMIN:
        modulos_acceso = Usuario.TODOS_MODULOS  # full access
    elif rol == Usuario.ROL_ADMIN and username:
        usuario = Usuario.objects.filter(user=username).first()
        modulos_acceso = list(usuario.modulos_acceso or []) if usuario else []

    return {
        "username": username,
        "rol": rol,
        "modulos_acceso": modulos_acceso,
        "is_superadmin": rol == Usuario.ROL_SUPERADMIN,
        "business": {
            "name": getattr(settings, "BUSINESS_NAME", "PetCare"),
            "nit": getattr(settings, "BUSINESS_NIT", "900123456-7"),
            "phone": getattr(settings, "BUSINESS_PHONE", "+57 300 000 0000"),
            "email": getattr(settings, "BUSINESS_EMAIL", "info@petcare.com"),
            "address": getattr(settings, "BUSINESS_ADDRESS", "Cra 00 # 00-00"),
            "city": getattr(settings, "BUSINESS_CITY", "Bogotá D.C."),
            "regimen": getattr(settings, "BUSINESS_REGIMEN", "Responsable de IVA"),
            "resolucion": getattr(settings, "BUSINESS_RESOLUCION_DIAN", "Resolución DIAN 18760000000000"),
        }
    }

