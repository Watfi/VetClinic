"""PyInstaller entrypoint for the desktop backend.

Bootstraps the Django runserver after running idempotent migrations and
seeding the default admin. ``VETCLINIC_DB_PATH`` and ``VETCLINIC_DATA_DIR``
should be set by the Electron host to point at writable locations
(typically ``%APPDATA%\\VetClinicDesktop\\``).
"""

import os
import sys
from pathlib import Path


def _bootstrap():
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hello.settings')

    import django
    django.setup()

    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)
    try:
        call_command('seed_admin')
    except Exception as exc:
        print(f'seed_admin skipped: {exc}', file=sys.stderr)
    call_command('collectstatic', interactive=False, verbosity=0)


def main():
    _bootstrap()
    bind = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1:8765'
    from django.core.management import execute_from_command_line
    execute_from_command_line([
        'manage.py', 'runserver', bind, '--noreload', '--insecure',
    ])


if __name__ == '__main__':
    main()
