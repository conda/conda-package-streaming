import contextlib
import os
import time

from conda_package_streaming.transmute import transmute


@contextlib.contextmanager
def timeme(message: str = ""):
    begin = time.time()
    yield
    end = time.time()
    print(f"{message}{end-begin:0.2f}s")


def test_transmute():
    import glob
    import tempfile

    conda_packages = []
    tarbz_packages = glob.glob(
        os.path.expanduser("~/miniconda3/pkgs/python-3.8.10-h0e5c897_0_cpython.tar.bz2")
    )

    with tempfile.TemporaryDirectory() as outdir:
        for packages in (conda_packages, tarbz_packages):
            for package in packages:
                with timeme(f"{package} took "):
                    transmute(package, outdir)
