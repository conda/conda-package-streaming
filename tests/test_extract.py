import io
import tarfile
from errno import ELOOP

import pytest

from conda_package_streaming import exceptions, extract, package_streaming

MAX_CONDAS = 8


def test_extract_stream(conda_paths, tmp_path):
    for i, package in enumerate(conda_paths):
        print(package)
        with open(package, "rb") as fileobj:
            stream = package_streaming.stream_conda_component(
                package, fileobj, component=package_streaming.CondaComponent.pkg
            )
            dest_dir = tmp_path / package.name
            extract.extract_stream(stream, dest_dir)

        if i >= MAX_CONDAS:
            break


def test_extract_all(conda_paths, tmp_path):
    for i, package in enumerate(conda_paths):
        print(package)
        dest_dir = tmp_path / package.name
        extract.extract(package, dest_dir=dest_dir)

        if i >= MAX_CONDAS:
            break


def empty_tarfile(name):
    """
    Return BytesIO containing a tarfile with one empty file named :name
    """
    tar = io.BytesIO()
    t = tarfile.TarFile(mode="w", fileobj=tar)
    t.addfile(tarfile.TarInfo(name=name), io.BytesIO())
    t.close()
    tar.seek(0)
    return tar


def test_oserror(tmp_path):
    """
    Fail if tarfile raises OSError (formerly known as IOError)
    """
    tar = empty_tarfile("empty-test")

    class TarELOOP(tarfile.TarFile):
        def extractall(self, path=None, members=None):
            raise OSError(ELOOP, "case sensitivity")

    class TarOSError(tarfile.TarFile):
        def extractall(self, path=None, members=None):
            raise OSError("not eloop")

    def stream(cls):
        yield (cls(fileobj=tar), tarfile.TarInfo())

    with pytest.raises(exceptions.CaseInsensitiveFileSystemError):
        extract.extract_stream(stream(TarELOOP), tmp_path)

    with pytest.raises(OSError):
        extract.extract_stream(stream(TarOSError), tmp_path)


def test_slip(tmp_path):
    """
    Fail if tarfile tries to put files outside its dest_dir (tmp_path)
    """

    def stream(fileobj):
        yield (tarfile.TarFile(fileobj=fileobj), tarfile.TarInfo())

    tar = empty_tarfile(name="../slip")

    with pytest.raises(exceptions.SafetyError):
        extract.extract_stream(stream(tar), tmp_path)

    tar2 = empty_tarfile(name="/absolute")

    with pytest.raises(exceptions.SafetyError):
        extract.extract_stream(stream(tar2), tmp_path)


def test_chown(conda_paths, tmp_path, mocker):
    for package in conda_paths[:2]:
        print(package)
        with open(package, "rb") as fileobj:
            stream = package_streaming.stream_conda_component(
                package, fileobj, component=package_streaming.CondaComponent.pkg
            )

            for tar, member in stream:
                assert isinstance(tar, package_streaming.TarfileNoSameOwner), tar
                break
