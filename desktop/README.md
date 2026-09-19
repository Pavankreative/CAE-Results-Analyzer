# Desktop app

Runs the API and the UI as one native window instead of two terminals plus a
browser tab. It is the same FastAPI backend and the same React build used in
the web setup — this is a launcher, not a separate application.

## Install

```bash
cd frontend && npm install && npm run build && cd ..
pip install -r backend/requirements-dev.txt
pip install -r desktop/requirements.txt
```

`pywebview` needs a native web-rendering backend that is already present on
most desktops:

- **Windows** — uses Edge WebView2 (installed by default on Windows 10/11).
- **macOS** — uses WKWebView, built in.
- **Linux** — needs GTK3 + WebKit2GTK (`sudo apt install python3-gi gir1.2-webkit2-4.1`
  on Debian/Ubuntu, or the Qt backend: `pip install pywebview[qt]`).

## Run

```bash
python desktop/desktop_app.py
```

A window titled "CAE Results Analyzer" opens at the same UI as the browser
version. If no display or web-rendering backend is available (for example,
inside a headless server or container), the script falls back to starting the
backend and opening your default browser instead — the application still
runs, just not in its own window.

## Rebuilding after a frontend change

The desktop shell serves the compiled `frontend/dist`, not the dev server, so
re-run the build after editing the frontend:

```bash
cd frontend && npm run build && cd ..
python desktop/desktop_app.py
```

## Packaging a standalone executable (optional, per OS)

This repository does not ship prebuilt binaries — a Windows `.exe`, a macOS
`.app` or a Linux binary each has to be built *on that OS* (PyInstaller does
not cross-compile). To build one on your own machine:

```bash
pip install pyinstaller
pyinstaller --name "CAE-Results-Analyzer" --onefile --add-data "frontend/dist:frontend/dist" desktop/desktop_app.py
```

The output lands in `dist/` (PyInstaller's own output folder, separate from
`frontend/dist`). Run it like any other installed application.
