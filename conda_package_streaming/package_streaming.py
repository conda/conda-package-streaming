"""
Unpack conda packages without using a temporary file.
"""

import bz2
import json
import os.path
import tarfile
import zipfile
from contextlib import closing

import zstandard  # or another zstandard binding that supports streams


def tar_generator(fileobj):
    """
    Yield (tar, member) from fileobj.
    """
    with closing(tarfile.open(fileobj=fileobj, mode="r|")) as tar:
        for member in tar:
            yield tar, member


def stream_conda_info(filename, fileobj=None):
    """
    Yield members from conda's embedded info/ tarball.

    For .tar.bz2 packages, yield all members.

    Yields (tar, member) tuples. You must only use the current member to
    prevent tar seeks and scans.

    To extract to disk, it's possible to call `tar.extractall(path)` on the
    first result and then ignore the rest of this generator. `extractall` takes
    care of some directory permissions/mtime issues, compared to `extract` or
    writing out the file objects yourself.
    """
    component = "info"
    return stream_conda_component(filename, fileobj, component)


def stream_conda_component(filename, fileobj=None, component="info"):
    """
    Yield members from .conda's embedded {component}- tarball. "info" or "pkg".

    For .tar.bz2 packages, yield all members.

    Yields (tar, member) tuples. You must only use the current member to
    prevent tar seeks and scans.

    To extract to disk, it's possible to call `tar.extractall(path)` on the
    first result and then ignore the rest of this generator. `extractall` takes
    care of some directory permissions/mtime issues, compared to `extract` or
    writing out the file objects yourself.
    """
    if filename.endswith(".conda"):
        zf = zipfile.ZipFile(fileobj or filename)
        file_id, _, _ = os.path.basename(filename).rpartition(".")
        component_name = f"{component}-{file_id}"
        component_filename = [
            info for info in zf.infolist() if info.filename.startswith(component_name)
        ]
        if not component_filename:
            raise RuntimeError(f"didn't find {component_name} component in {filename}")
        assert len(component_filename) == 1
        reader = zstandard.ZstdDecompressor().stream_reader(
            zf.open(component_filename[0])
        )
    elif filename.endswith(".tar.bz2"):
        reader = bz2.open(fileobj or filename, mode="rb")
    return tar_generator(reader)


def test():
    import glob

    conda_packages = glob.glob(os.path.expanduser("~/miniconda3/pkgs/*.conda"))
    tarbz_packages = glob.glob(os.path.expanduser("~/miniconda3/pkgs/*.tar.bz2"))

    for packages in (conda_packages, tarbz_packages):
        for package in packages:
            print(package)
            stream = iter(stream_conda_info(package))
            found = False
            for tar, member in stream:
                assert not found, "early exit did not work"
                if member.name == "info/index.json":
                    json.load(tar.extractfile(member))
                    found = True
                    stream.close()  # PEP 342 close()
            assert found, f"index.json not found in {package}"


if __name__ == "__main__":
    test()
