'use strict';

const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const { execFile } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

// The Studio is a thin shell over the CLI: it never reimplements install logic.
const FRAMEWORK_ROOT = process.env.DMAD_ROOT
  ? path.resolve(process.env.DMAD_ROOT)
  : path.resolve(__dirname, '..', '..');
const INSTALLER = path.join(FRAMEWORK_ROOT, 'install.py');

const PROVIDER_ID = /^[a-z0-9][a-z0-9-]*$/;

let pythonCommand = null;

function execFileAsync(command, args) {
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true, maxBuffer: 4 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        error.stdout = stdout;
        error.stderr = stderr;
        reject(error);
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

async function resolvePython() {
  if (pythonCommand) return pythonCommand;

  const candidates =
    process.platform === 'win32'
      ? [['py', ['-3']], ['python', []], ['python3', []]]
      : [['python3', []], ['python', []]];

  for (const [command, prefix] of candidates) {
    try {
      const { stdout } = await execFileAsync(command, [...prefix, '--version']);
      if (/^Python 3\.(1[1-9]|[2-9]\d)/.test(stdout.trim())) {
        pythonCommand = [command, prefix];
        return pythonCommand;
      }
    } catch {
      // try the next candidate
    }
  }
  throw new Error('Python 3.11 or newer was not found on your PATH. Install it, then reopen DMAD Studio.');
}

async function runInstaller(args) {
  if (!fs.existsSync(INSTALLER)) {
    throw new Error(`Could not find install.py at ${INSTALLER}. Set DMAD_ROOT to your DMAD checkout.`);
  }
  const [command, prefix] = await resolvePython();
  // execFile with an argument array — never a shell string — so paths cannot inject commands.
  try {
    const { stdout } = await execFileAsync(command, [...prefix, INSTALLER, ...args]);
    return JSON.parse(stdout);
  } catch (error) {
    // Handled installer failures exit 1 but still print a JSON body on stdout.
    if (error.stdout) {
      try {
        return JSON.parse(error.stdout);
      } catch {
        // fall through to the generic error below
      }
    }
    throw new Error((error.stderr || '').trim() || error.message);
  }
}

function assertFolder(target) {
  if (typeof target !== 'string' || !target.trim()) {
    throw new Error('Choose a folder first.');
  }
  const resolved = path.resolve(target);
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
    throw new Error(`Not a folder: ${resolved}`);
  }
  return resolved;
}

function sanitizeProviders(providers) {
  if (!Array.isArray(providers) || providers.length === 0) {
    throw new Error('Select at least one AI tool.');
  }
  const clean = providers.filter((id) => typeof id === 'string' && PROVIDER_ID.test(id));
  if (clean.length !== providers.length) {
    throw new Error('Invalid provider selection.');
  }
  return clean;
}

ipcMain.handle('dmad:describe', async () => {
  const info = await runInstaller(['--describe']);
  return { ...info, frameworkRoot: FRAMEWORK_ROOT, userName: os.userInfo().username };
});

ipcMain.handle('dmad:pick-folder', async (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  const result = await dialog.showOpenDialog(window, {
    title: 'Choose a project folder',
    properties: ['openDirectory', 'createDirectory'],
    buttonLabel: 'Select folder',
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

ipcMain.handle('dmad:inspect', async (_event, target) => {
  const folder = assertFolder(target);
  const info = await runInstaller(['--inspect', '--target', folder]);
  const entries = fs.readdirSync(folder).filter((name) => name !== '.DS_Store');
  return { ...info, isEmpty: entries.length === 0 };
});

ipcMain.handle('dmad:install', async (_event, options) => {
  const folder = assertFolder(options?.target);
  const providers = sanitizeProviders(options?.providers);
  return runInstaller([
    '--target', folder,
    '--providers', ...providers,
    '--project-name', path.basename(folder),
    '--user-name', os.userInfo().username,
    '--json',
  ]);
});

ipcMain.handle('dmad:open-folder', async (_event, target) => {
  await shell.openPath(assertFolder(target));
});

function createWindow() {
  const window = new BrowserWindow({
    width: 780,
    height: 720,
    minWidth: 620,
    minHeight: 560,
    backgroundColor: '#14161c',
    title: 'DMAD Studio',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  window.removeMenu();
  window.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event) => event.preventDefault());
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
