from django.conf import settings

def user_context(request):
    return {
        "username": request.session.get("user"),
        "rol": request.session.get("rol"),
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

