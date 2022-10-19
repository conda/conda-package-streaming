import contextlib
import os
import tarfile
import tempfile
import time
from pathlib import Path

from conda_package_streaming.transmute import transmute


@contextlib.contextmanager
def timeme(message: str = ""):
    begin = time.time()
    yield
    end = time.time()
    print(f"{message}{end-begin:0.2f}s")


def test_transmute(conda_paths):

    tarbz_packages = []
    for path in conda_paths:
        path = str(path)
        if path.endswith(".tar.bz2") and (1 << 20 < os.stat(path).st_size < 1 << 22):
            tarbz_packages = [path]
    conda_packages = []  # not supported

    assert tarbz_packages, "no medium-sized package found"

    with tempfile.TemporaryDirectory() as outdir:
        for packages in (conda_packages, tarbz_packages):
            for package in packages:
                with timeme(f"{package} took "):
                    transmute(package, outdir)


def test_transmute_symlink(tmpdir):
    testtar = Path(tmpdir, "test.tar.bz2")
    with tarfile.open(testtar, "w:bz2") as tar:
        symlink = tarfile.TarInfo(name="symlink")
        symlink.type = tarfile.LNKTYPE
        symlink.linkname = "target"
        tar.addfile(symlink)

    transmute(str(testtar), tmpdir)
