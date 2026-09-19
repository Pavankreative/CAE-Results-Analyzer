#!/usr/bin/env python3
"""CAE Results Analyzer — Desktop launcher.

Runs the FastAPI backend in a background thread and opens the application in
a native desktop window (via pywebview), so the whole thing starts with one
command and one process instead of two terminals and a browser tab.

    python desktop/desktop_app.py

Requires the frontend to be built first (frontend/dist must exist):

    cd frontend && npm install && npm run build && cd ..
    python desktop/desktop_app.py
"""
from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

HOST = "127.0.0.1"
PORT = 8000


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) != 0


def _wait_until_up(port: int, timeout: float = 15.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def start_server(port: int) -> None:
    """Run uvicorn in-process. Call this in a daemon thread."""
    import uvicorn
    from app.main import app  # noqa: E402  (path inserted above)
    uvicorn.run(app, host=HOST, port=port, log_level="info")


def main() -> int:
    import logging
    logging.getLogger("pywebview").setLevel(logging.CRITICAL)
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        print("frontend/dist not found.")
        print("Build it first:")
        print("  cd frontend && npm install && npm run build")
        return 1

    port = PORT if _port_free(PORT) else PORT + 1
    thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    thread.start()

    if not _wait_until_up(port):
        print("Backend did not respond in time; check the console output above.")
        return 1

    url = f"http://{HOST}:{port}/"
    try:
        import webview
        window = webview.create_window(
            "CAE Results Analyzer", url, width=1440, height=900, min_size=(1024, 680),
        )
        webview.start()
    except Exception as exc:  # no display, missing GTK/Qt backend, headless CI, etc.
        print(f"Could not open a native window ({exc}).")
        print(f"Opening in your default browser instead: {url}")
        webbrowser.open(url)
        print("Press Ctrl+C to stop the server.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
