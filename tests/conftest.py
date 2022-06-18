from pathlib import Path

import pytest
import server


@pytest.fixture(scope="session")
def package_server():
    thread = server.get_server_thread()
    thread.start()
    return thread


@pytest.fixture(scope="session")
def conda_paths(package_server):
    pkgs_dir = Path(package_server.app.pkgs_dir)
    conda_paths = []
    for path in pkgs_dir.iterdir():
        if path.name.endswith((".tar.bz2", ".conda")):
            conda_paths.append(path)
    return conda_paths
