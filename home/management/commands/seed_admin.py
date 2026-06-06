from django.core.management.base import BaseCommand

from home.models import Usuario


class Command(BaseCommand):
    help = "Create the initial Administrator account if no admin exists."

    def add_arguments(self, parser):
        parser.add_argument("--user", default="admin")
        parser.add_argument("--email", default="admin@local")
        parser.add_argument("--password", default="admin123")
        parser.add_argument("--nombre", default="Administrator")

    def handle(self, *args, **opts):
        if Usuario.objects.filter(rol=Usuario.ROL_ADMIN).exists():
            self.stdout.write(self.style.WARNING(
                "An administrator already exists; skipping."
            ))
            return

        admin = Usuario.objects.create(
            user=opts["user"],
            email=opts["email"],
            password=opts["password"],
            nombre=opts["nombre"],
            rol=Usuario.ROL_ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Created administrator '{admin.user}'. "
            f"Default password is '{opts['password']}' — change it after first login."
        ))
