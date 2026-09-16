# DMAD Studio

A desktop app for installing the [DMAD](../README.md) agent framework into any project folder — pick a folder, tick your AI tools, click once.

> DMAD Studio is **optional**. The framework is CLI-first and fully usable without it:
> `python install.py --target . --providers copilot`

## How it works

Studio is a thin Electron shell over the existing installer. It does not reimplement any
install logic — it shells out to `install.py --json` and renders the result. One source of
truth, so the GUI can never drift from the CLI.

```
renderer (HTML/CSS/JS)  ->  preload (contextBridge)  ->  main process  ->  python install.py --json
```

## Run it

From this folder:

```bash
npm install
npm start
```

Requires **Node 18+** (to run Electron) and **Python 3.11+** on your PATH (to run the
installer). Studio detects Python automatically and tells you if it's missing.

## Using it

1. **Browse…** and pick any folder — empty or an existing project. Studio tells you which
   it found, and whether DMAD is already installed there.
2. Tick the AI tools you use. The list is read live from `dmad/manifest.toml`, so adding a
   provider to the framework makes it appear here with no code change.
3. Click **Install DMAD**. If the folder already has DMAD, the button becomes **Update**.

Existing files are never overwritten — `_dmad/config.toml` and everything in `_dmad/custom/`
survive updates, exactly as with the CLI.

## Locating the framework

Studio looks for `install.py` two levels up from `src/` (the repo root). To point it at a
different DMAD checkout, set `DMAD_ROOT`:

```powershell
$env:DMAD_ROOT = "C:\path\to\DMAD"; npm start
```

## Security notes

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`
- The renderer gets no Node or raw IPC access — only the five methods in `src/preload.js`
- Python is invoked with `execFile` and an argument **array**, never a shell string, so
  folder paths cannot inject commands
- Provider ids are validated against `^[a-z0-9][a-z0-9-]*$` before being passed through
- A strict CSP blocks remote script/style loading; in-app navigation and popups are denied

## Layout

```
src/
  main.js              window, IPC handlers, Python discovery, installer invocation
  preload.js           contextBridge surface
  renderer/
    index.html         markup + CSP
    styles.css
    renderer.js        UI state
```
