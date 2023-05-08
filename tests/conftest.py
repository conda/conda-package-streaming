import json
import logging
import os.path
import shutil
import subprocess
from pathlib import Path

import pytest
import server

from conda_package_streaming.transmute import transmute_tar_bz2

log = logging.getLogger(__name__)


LIMIT_TEST_PACKAGES = 16


def find_packages_dirs() -> Path:
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

    return Path(first_pkg_dir)


@pytest.fixture(scope="session")
def pkgs_dir(tmp_path_factory):
    """
    Dedicated test package directory.
    """
    return tmp_path_factory.mktemp("pkgs")


@pytest.fixture(scope="session")
def package_server(pkgs_dir, conda_paths):
    thread = server.get_server_thread(pkgs_dir)
    thread.start()
    return thread


@pytest.fixture(scope="session")
def conda_paths(pkgs_dir: Path):
    found_packages = find_packages_dirs()
    conda_paths = []
    for path in found_packages.iterdir():
        if path.name.endswith((".tar.bz2", ".conda")):
            conda_paths.append(path)

    return add_tar_bz2s(conda_paths, pkgs_dir)


def add_tar_bz2s(paths: list[Path], pkgs_dir: Path):
    """
    If there aren't enough .tar.bz2's available, create some from available
    .conda's. Return paths.
    """
    conda_paths: list[Path] = []
    tarbz2_paths: list[Path] = []
    output_paths: list[Path] = []

    assert isinstance(pkgs_dir, Path)

    for path in paths:
        if path.name.endswith(".tar.bz2"):
            tarbz2_paths.append(path)
        elif path.name.endswith(".conda"):
            conda_paths.append(path)

    tarbz2_path: Path = pkgs_dir

    medium_conda_paths = []
    for path in conda_paths:
        if 1 << 20 < path.stat().st_size < 1 << 22:
            medium_conda_paths.append(path)
    medium_conda_paths = medium_conda_paths[:LIMIT_TEST_PACKAGES]

    # this ignores existing .tar.bz2 for simplicity (.tar.bz2 is missing in CI)
    for conda in set(medium_conda_paths + conda_paths[:10]):
        shutil.copy(conda, tarbz2_path)
        transmute_tar_bz2(str(conda), tarbz2_path)

    output_paths.extend(tarbz2_path.glob("*.tar.bz2"))
    output_paths.extend(tarbz2_path.glob("*.conda"))

    return sorted(output_paths)  # sort interleaves .tar.bz2 and .conda
