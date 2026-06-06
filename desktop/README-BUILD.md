# VetClinic Desktop — build

Local-first Django + Electron app, packaged as a Windows installer.
No internet, no MongoDB, no Python required on the end-user's machine.

## One-time prerequisites (developer machine)

- Python 3.13+
- Node.js 20+
- `pip install -r requirements-build.txt`
- `cd desktop && npm install`

## Run in dev (uses your local Python)

```
cd desktop
npm run dev
```

Electron opens, spawns `python manage.py runserver` on a free port,
loads `/login/`. Default credentials: `admin / admin123`.

The user-data directory is `%APPDATA%\VetClinic Desktop\`. Delete it to
reset the local DB.

## Produce a Windows installer

```
# 1. From repo root: build the seed DB (db.sqlite3) and collected static files
cd ..
python manage.py migrate
python manage.py seed_admin
python manage.py collectstatic --noinput

# 2. Freeze the Django backend into a single-folder executable
cd desktop
npm run build:backend

# 3. Bundle Electron + the backend exe into an NSIS installer
npm run dist
```

Output: `dist-electron/VetClinic Desktop Setup 1.0.0.exe`.

## What the installer ships

- `resources/backend/vetclinic-backend.exe` — frozen Django (PyInstaller)
- `resources/staticfiles/` — collected static assets
- `resources/seed/db.sqlite3` — seed DB with the default admin

On first launch the seed DB is copied to `%APPDATA%\VetClinic Desktop\db.sqlite3`;
subsequent launches reuse it, so user data persists across reinstalls of the
same major version.
