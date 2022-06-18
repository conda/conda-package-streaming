"""
Test web server.
"""
import json
import logging
import os
import os.path
import subprocess
import threading
import wsgiref.simple_server
from typing import Any

import bottle

log = logging.getLogger(__name__)


def find_packages_dirs():
    """
    Ask conda for package directories.
    """
    conda_info = json.loads(
        subprocess.run(
            [os.environ["CONDA_EXE"], "info", "--json"],
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
    )

    # XXX can run individual environment's conda (base conda is more likely to
    # have useful cached packages)
    pkgs_dirs = conda_info["pkgs_dirs"] + [os.path.expanduser("~/miniconda3/pkgs")]

    log.debug("search %s", pkgs_dirs)

    first_pkg_dir = next(path for path in pkgs_dirs if os.path.exists(path))

    return first_pkg_dir


def get_app():
    """
    Bottle conveniently supports Range requests.

    Server may block if browser etc. keeps connection open.
    """
    app = bottle.Bottle()
    pkgs_dir = find_packages_dirs()
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
    t = get_server_thread()
    t.start()

    import time

    time.sleep(300)


class ServerThread(threading.Thread):
    server: wsgiref.simple_server.WSGIServer
    app: Any


def get_server_thread():
    """
    Return test server thread with additional .server, .app properties.

    Call .start() to serve in the background.
    """
    app = get_app()
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
