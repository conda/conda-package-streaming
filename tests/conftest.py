from pathlib import Path

import pytest
import server

from conda_package_streaming.transmute import transmute_tar_bz2


@pytest.fixture(scope="session")
def package_server():
    thread = server.get_server_thread()
    thread.start()
    return thread


@pytest.fixture(scope="session")
def conda_paths(package_server, tmp_path_factory):
    pkgs_dir = Path(package_server.app.pkgs_dir)
    conda_paths = []
    for path in pkgs_dir.iterdir():
        if path.name.endswith((".tar.bz2", ".conda")):
            conda_paths.append(path)

    add_tar_bz2s(conda_paths, tmp_path_factory)

    return conda_paths


def add_tar_bz2s(paths: list[Path], tmp_path_factory):
    """
    If there aren't enough .tar.bz2's available, create some from available
    .conda's; append to paths list.
    """
    conda_paths: list[Path] = []
    tarbz2_paths: list[Path] = []
    for path in paths:
        if path.name.endswith(".tar.bz2"):
            tarbz2_paths.append(path)
        elif path.name.endswith(".conda"):
            conda_paths.append(path)

    tarbz2_path = tmp_path_factory.mktemp("pkgs")

    if len(tarbz2_paths) < 10:
        for conda in conda_paths[:10]:
            transmute_tar_bz2(str(conda), tarbz2_path)
