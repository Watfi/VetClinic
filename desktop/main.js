const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');

const isDev = !app.isPackaged;

let backendProcess = null;
let backendPort = null;

function findFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
  });
}

function ensureUserData() {
  const userData = app.getPath('userData');
  fs.mkdirSync(userData, { recursive: true });
  fs.mkdirSync(path.join(userData, 'media'), { recursive: true });
  fs.mkdirSync(path.join(userData, 'staticfiles'), { recursive: true });

  const dbPath = path.join(userData, 'db.sqlite3');
  if (!fs.existsSync(dbPath)) {
    const seedDb = isDev
      ? path.join(__dirname, '..', 'db.sqlite3')
      : path.join(process.resourcesPath, 'seed', 'db.sqlite3');
    if (fs.existsSync(seedDb)) {
      fs.copyFileSync(seedDb, dbPath);
    }
  }

  if (!isDev) {
    const seedStatic = path.join(process.resourcesPath, 'staticfiles');
    if (fs.existsSync(seedStatic)) {
      // Mirror packaged static assets so WhiteNoise can serve them.
      copyDir(seedStatic, path.join(userData, 'staticfiles'));
    }
  }

  return { userData, dbPath };
}

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function startBackend(port, userData, dbPath) {
  const env = {
    ...process.env,
    VETCLINIC_DB_PATH: dbPath,
    VETCLINIC_DATA_DIR: userData,
    PYTHONIOENCODING: 'utf-8',
    VETCLINIC_DATABASE_URL:
      process.env.VETCLINIC_DATABASE_URL ||
      'postgresql://postgres.bjhkqkxdeveaxliiuvzc:MVSXVETCLINIC2026$@aws-1-us-east-1.pooler.supabase.com:6543/postgres',
  };

  let cmd, args, cwd;
  if (isDev) {
    const repoRoot = path.join(__dirname, '..');
    cmd = process.platform === 'win32' ? 'python' : 'python3';
    args = ['manage.py', 'runserver', `127.0.0.1:${port}`, '--noreload', '--insecure'];
    cwd = repoRoot;
  } else {
    cmd = path.join(process.resourcesPath, 'backend', 'vetclinic-backend.exe');
    args = [`127.0.0.1:${port}`];
    cwd = path.dirname(cmd);
  }

  backendProcess = spawn(cmd, args, { env, cwd, stdio: 'inherit' });
  backendProcess.on('exit', (code) => {
    console.log(`backend exited with ${code}`);
    backendProcess = null;
  });
}

function waitForBackend(port, timeoutMs = 90000) {
  const url = `http://127.0.0.1:${port}/login/`;
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode < 500) return resolve();
        retry();
      });
      req.on('error', retry);
      req.setTimeout(1000, () => req.destroy());
    };
    const retry = () => {
      if (Date.now() > deadline) return reject(new Error('Backend did not start in time.'));
      setTimeout(tick, 200);
    };
    tick();
  });
}

async function createWindow() {
  try {
    const { userData, dbPath } = ensureUserData();
    backendPort = await findFreePort();
    startBackend(backendPort, userData, dbPath);
    await waitForBackend(backendPort);
  } catch (err) {
    dialog.showErrorBox('VetClinic Desktop', `Failed to start backend:\n${err.message}`);
    app.quit();
    return;
  }

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    autoHideMenuBar: true,
    title: 'VetClinic Desktop',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  win.loadURL(`http://127.0.0.1:${backendPort}/login/`);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) {
    try { backendProcess.kill(); } catch (_) {}
    backendProcess = null;
  }
});
