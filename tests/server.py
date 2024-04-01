"""
Test web server.
"""

import logging
import threading
import wsgiref.simple_server
from pathlib import Path
from typing import Any

import bottle
import conftest

log = logging.getLogger(__name__)


def get_app(pkgs_dir):
    """
    Bottle conveniently supports Range requests.

    Server may block if browser etc. keeps connection open.
    """
    app = bottle.Bottle()
    app.pkgs_dir = pkgs_dir

    def serve_file(filename):
        mimetype = "auto"
        # from https://repo.anaconda.com/ behavior:
        if filename.endswith(".tar.bz2"):
            mimetype = "application/x-tar"
        elif filename.endswith(".conda"):
            mimetype = "binary/octet-stream"
        return bottle.static_file(filename, root=pkgs_dir, mimetype=mimetype)

    app.route("/pkgs/<filename>", "GET", serve_file)
    return app


def selftest():
    """
    Run server in a thread that will die when the application exits.
    """
    t = get_server_thread(conftest.find_packages_dirs())
    t.start()

    import time

    time.sleep(300)


class ServerThread(threading.Thread):
    server: wsgiref.simple_server.WSGIServer
    app: Any


def get_server_thread(pkgs_dir: Path):
    """
    Return test server thread with additional .server, .app properties.

    Call .start() to serve in the background.
    """
    app = get_app(pkgs_dir)
    server = wsgiref.simple_server.make_server("127.0.0.1", 0, app)
    log.info(f"serving {app.pkgs_dir} on {server.server_address}/pkgs")
    t = ServerThread(daemon=True, target=server.serve_forever)
    t.app = app
    t.server = server  # server.application == app
    return t


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    log.setLevel(logging.DEBUG)
    selftest()
