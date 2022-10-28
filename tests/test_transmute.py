import contextlib
import io
import os
import tarfile
import time
from pathlib import Path

import pytest

from conda_package_streaming.package_streaming import (
    CondaComponent,
    stream_conda_component,
)
from conda_package_streaming.transmute import transmute, transmute_tar_bz2


@pytest.fixture
def testtar_bytes():
    buffer = io.BytesIO()
    with tarfile.open("test.tar.bz2", "w:bz2", fileobj=buffer) as tar:
        symlink = tarfile.TarInfo(name="symlink")
        symlink.type = tarfile.LNKTYPE
        symlink.linkname = "target"
        tar.addfile(symlink)

        expected = tarfile.TarInfo(name="info/expected")
        tar.addfile(expected, io.BytesIO())
        unexpected = tarfile.TarInfo(name="info/unexpected")
        tar.addfile(unexpected, io.BytesIO())
    return buffer.getbuffer()


@contextlib.contextmanager
def timeme(message: str = ""):
    begin = time.time()
    yield
    end = time.time()
    print(f"{message}{end-begin:0.2f}s")


def test_transmute(conda_paths, tmpdir):

    tarbz_packages = []
    for path in conda_paths:
        path = str(path)
        if path.endswith(".tar.bz2") and (1 << 20 < os.stat(path).st_size < 1 << 22):
            tarbz_packages = [path]
    conda_packages = []  # not supported

    assert tarbz_packages, "no medium-sized .tar.bz2 packages found"

    for packages in (conda_packages, tarbz_packages):
        for package in packages:
            with timeme(f"{package} took "):
                transmute(package, tmpdir)


def test_transmute_symlink(tmpdir, testtar_bytes):
    testtar = Path(tmpdir, "test.tar.bz2")
    testtar.write_bytes(testtar_bytes)

    transmute(str(testtar), tmpdir)


def test_transmute_info_filter(tmpdir, testtar_bytes):
    testtar = Path(tmpdir, "test.tar.bz2")
    testtar.write_bytes(testtar_bytes)

    transmute(
        str(testtar), tmpdir, is_info=lambda filename: filename == "info/expected"
    )

    with open(Path(tmpdir, "test.conda"), "rb") as fileobj:
        for component, expected in (CondaComponent.info, {"info/expected"}), (
            CondaComponent.pkg,
            {
                "info/unexpected",
                "symlink",
            },
        ):
            items = stream_conda_component("test.conda", fileobj, component)
            assert set(member.name for tar, member in items) == expected, items


def test_transmute_backwards(tmpdir, conda_paths):

    tarbz_packages = []
    for path in conda_paths:
        path = str(path)
        if path.endswith(".conda") and (1 << 20 < os.stat(path).st_size < 1 << 22):
            tarbz_packages = [path]
    conda_packages = []  # not supported

    assert tarbz_packages, "no medium-sized .conda packages found"

    for packages in (conda_packages, tarbz_packages):
        for package in packages:
            with timeme(f"{package} took "):
                transmute_tar_bz2(package, tmpdir)


def test_transmute_tarbz2_to_tarbz2(tmpdir, testtar_bytes):
    testtar = Path(tmpdir, "test.tar.bz2")
    testtar.write_bytes(testtar_bytes)
    outdir = Path(tmpdir, "output")
    outdir.mkdir()
    transmute_tar_bz2(str(testtar), outdir)
