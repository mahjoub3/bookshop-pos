"""Desktop launcher for the Bookshop app."""
import html
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(BASE))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop.settings")

import django  # noqa: E402
django.setup()

from django.core.management import call_command  # noqa: E402

_server_error = {}


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(port):
    try:
        from wsgiref.simple_server import make_server
        from django.core.wsgi import get_wsgi_application

        application = get_wsgi_application()
        httpd = make_server("127.0.0.1", port, application)
        httpd.serve_forever()
    except Exception:
        _server_error["tb"] = traceback.format_exc()


def wait_for_server(port, timeout=20.0):
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/"
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.3)
            return True
        except Exception:
            time.sleep(0.15)
    return False


def main():
    try:
        call_command("migrate", interactive=False, verbosity=0)
    except Exception:
        _server_error["tb"] = "Migration error:\n" + traceback.format_exc()

    port = find_free_port()
    threading.Thread(target=run_server, args=(port,), daemon=True).start()

    ready = wait_for_server(port)

    import webview
    if not ready:
        err = _server_error.get("tb") or "(no traceback captured)"
        err_html = html.escape(err)
        webview.create_window(
            "Bookshop — startup failed",
            html=(
                "<h2>Could not start the local server.</h2>"
                f"<pre style='background:#f0f0f0;padding:12px;overflow:auto;"
                f"max-height:500px;font-size:12px'>{err_html}</pre>"
            ),
            width=900,
            height=600,
        )
    else:
        webview.create_window(
            "Bookshop",
            f"http://127.0.0.1:{port}/",
            width=1280,
            height=800,
            min_size=(1024, 640),
        )
    webview.start()


if __name__ == "__main__":
    main()