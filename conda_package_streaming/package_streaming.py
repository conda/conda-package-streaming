"""
Unpack conda packages without using a temporary file.
"""

from __future__ import annotations

import bz2
import os.path
import tarfile
import zipfile
from enum import Enum
from typing import Generator

try:
    import zstandard
except ImportError:
    import warnings

    warnings.warn("zstandard could not be imported. Running without .conda support.")

    zstandard = None


class CondaComponent(Enum):
    pkg = "pkg"
    info = "info"

    def __str__(self):
        return self.value


class TarfileNoSameOwner(tarfile.TarFile):
    def chown(self, tarinfo, targetpath, numeric_owner):
        """
        Override chown to be a no-op, since we don't want to preserve ownership
        here. (tarfile.TarFile only lets us toggle all of (chown, chmod, mtime))
        """
        return


def tar_generator(
    fileobj, tarfile_open=TarfileNoSameOwner.open
) -> Generator[tuple[tarfile.TarFile, tarfile.TarInfo], None, None]:
    """
    Yield (tar, member) from fileobj.
    """
    # tarfile will not close fileobj because _extfileobj is True
    # caller should take care to close files all the way back to the http request...
    with tarfile_open(fileobj=fileobj, mode="r|") as tar:
        for member in tar:
            yield tar, member


def stream_conda_info(
    filename, fileobj=None
) -> Generator[tuple[tarfile.TarFile, tarfile.TarInfo], None, None]:
    """
    Yield members from conda's embedded info/ tarball.

    For .tar.bz2 packages, yield all members.

    Yields (tar, member) tuples. You must only use the current member to
    prevent tar seeks and scans.

    To extract to disk, it's possible to call ``tar.extractall(path)`` on the
    first result and then ignore the rest of this generator. ``extractall`` takes
    care of some directory permissions/mtime issues, compared to ``extract`` or
    writing out the file objects yourself.
    """
    component = "info"
    return stream_conda_component(filename, fileobj, component)


def stream_conda_component(
    filename, fileobj=None, component: CondaComponent | str = CondaComponent.pkg
) -> Generator[tuple[tarfile.TarFile, tarfile.TarInfo], None, None]:
    """
    Yield members from .conda's embedded {component}- tarball. "info" or "pkg".

    For .tar.bz2 packages, yield all members.

    Yields (tar, member) tuples. You must only use the current member to
    prevent tar seeks and scans.

    To extract to disk, it's possible to call ``tar.extractall(path)`` on the
    first result and then ignore the rest of this generator. ``extractall`` takes
    care of some directory permissions/mtime issues, compared to ``extract`` or
    writing out the file objects yourself.
    """
    if str(filename).endswith(".conda"):
        if zstandard is None:
            raise RuntimeError("Cannot unpack `.conda` without zstandard")

        zf = zipfile.ZipFile(fileobj or filename)
        file_id, _, _ = os.path.basename(filename).rpartition(".")
        component_name = f"{component}-{file_id}"
        component_filename = [
            info for info in zf.infolist() if info.filename.startswith(component_name)
        ]
        if not component_filename:
            raise LookupError(f"didn't find {component_name} component in {filename}")
        assert len(component_filename) == 1
        reader = zstandard.ZstdDecompressor().stream_reader(
            zf.open(component_filename[0])
        )
    elif str(filename).endswith(".tar.bz2"):
        reader = bz2.open(fileobj or filename, mode="rb")
    else:
        raise ValueError("unsupported file extension")
    return tar_generator(reader)
