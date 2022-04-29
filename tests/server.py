"""
Test web server.
"""
import subprocess
import os
import os.path
import json
import threading
import wsgiref.simple_server

import bottle


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

    # XXX can run individual environment's conda
    pkgs_dirs = conda_info["pkgs_dirs"] + [os.path.expanduser("~/miniconda3/pkgs")]

    print(f"search {pkgs_dirs}")

    first_pkg_dir = next(path for path in pkgs_dirs if os.path.exists(path))

    return first_pkg_dir


def get_app():
    """
    Bottle conveniently supports Range requests.
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

    app.route("/pkgs/<filename>", ["GET"], serve_file)
    return app


def selftest():
    """
    Run server in a thread that will die when the application exits.
    """
    app = get_app()
    server = wsgiref.simple_server.make_server("127.0.0.1", 0, app)
    print(f"serving {app.pkgs_dir} on {server.server_address}/pkgs")
    threading.Thread(daemon=True, target=server.serve_forever).start()
    import time

    time.sleep(300)


if __name__ == "__main__":
    selftest()
