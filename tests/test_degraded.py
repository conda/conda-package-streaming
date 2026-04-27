"""
Allow conda_package_streaming to work in .tar.bz2-only mode if zstd support is
not available.
"""

import importlib
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest


def test_degraded(tmpdir):
    try:
        sys.modules["backports.zstd"] = None  # type: ignore
        sys.modules["compression.zstd"] = None  # type: ignore

        import conda_package_streaming.extract
        import conda_package_streaming.package_streaming

        importlib.reload(conda_package_streaming.package_streaming)

        testconda = Path(tmpdir, "testconda.conda")
        with zipfile.ZipFile(testconda, "w"):
            pass

        testtar = Path(tmpdir, "test.tar.bz2")
        with tarfile.open(testtar, "w:bz2") as tar:
            tar.addfile(tarfile.TarInfo(name="jim"))

        for (
            tar,
            _,
        ) in conda_package_streaming.package_streaming.stream_conda_component(testtar):
            pass

        with pytest.raises(RuntimeError):
            for (
                tar,
                _,
            ) in conda_package_streaming.package_streaming.stream_conda_component(
                testconda
            ):
                pass  # pragma: no cover

        with pytest.raises(RuntimeError):
            conda_package_streaming.extract.extract(testconda, tmpdir)

    finally:
        sys.modules.pop("compression.zstd", None)
        sys.modules.pop("backports.zstd", None)

        import conda_package_streaming.package_streaming

        importlib.reload(conda_package_streaming.package_streaming)
        assert conda_package_streaming.package_streaming.zstd
