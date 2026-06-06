import os, django, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE","Hello.settings")
django.setup()
from django.test import Client
c = Client(HTTP_HOST="127.0.0.1")
s = c.session; s["user"]="admin"; s["rol"]="Administrador"; s.save()
for p in ["/categorias/","/productos/","/ventas/","/recetas/"]:
    try:
        r = c.get(p)
        print(p, r.status_code)
        if r.status_code >= 500:
            print(r.content[:3000].decode("utf8","ignore"))
    except Exception:
        traceback.print_exc()
