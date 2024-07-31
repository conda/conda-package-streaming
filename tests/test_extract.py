import io
import stat
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


def empty_tarfile(name, mode=0o644, tar_mode="w"):
    """
    Return BytesIO containing a tarfile with one empty file named :name
    """
    tar = io.BytesIO()
    t = tarfile.open(mode=tar_mode, fileobj=tar)
    tarinfo = tarfile.TarInfo(name=name)
    tarinfo.mode = mode
    t.addfile(tarinfo, io.BytesIO())
    t.close()
    tar.seek(0)
    return tar


def not_unicode_tarbz2(
    name=b"\x80\x81".decode("utf-8", errors="surrogateescape"), mode=0o644
):
    """
    Return BytesIO containing a tarfile with one empty file named :name
    """
    return empty_tarfile(name=name, tar_mode="w:bz2")


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


def stream(fileobj):
    """
    Like the tuples produced by part of conda-package-streaming.
    """
    yield (package_streaming.TarfileNoSameOwner(fileobj=fileobj), tarfile.TarInfo())


def stream_stdlib(fileobj):
    """
    Like the tuples produced by part of conda-package-streaming.
    """
    yield (tarfile.TarFile(fileobj=fileobj), tarfile.TarInfo())


def test_slip(tmp_path):
    """
    Fail if tarfile tries to put files outside its dest_dir (tmp_path)
    """

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


def test_umask(tmp_path, mocker):
    """
    Demonstrate that umask-respecting tar implementation works.

    Mock umask in case it is different on your system.
    """
    mocker.patch("conda_package_streaming.package_streaming.UMASK", new=0o22)

    tar3 = empty_tarfile(name="naughty_umask", mode=0o777)
    extract.extract_stream(stream_stdlib(tar3), tmp_path)
    mode = (tmp_path / "naughty_umask").stat().st_mode
    assert mode & stat.S_IWGRP, "%o" % mode

    tar3.seek(0)
    extract.extract_stream(stream(tar3), tmp_path)
    mode = (tmp_path / "naughty_umask").stat().st_mode
    assert not mode & stat.S_IWGRP, "%o" % mode


def test_encoding():
    """
    Some users do not have "utf-8" as the default sys.getfilesystemencoding() or
    sys.getdefaultencoding(). Instead of trying to change the system encoding,
    we prove that stream_conda_component honors the new passed-in encoding which
    is now "utf-8" by default.
    """

    tar = not_unicode_tarbz2()

    # Use new default encoding of "utf-8" regardless of what the system says.
    stream = package_streaming.stream_conda_component(
        "package.tar.bz2", tar, component="pkg"
    )

    with pytest.raises(UnicodeEncodeError):
        for t, member in stream:
            member.name.encode("utf-8")
            print(t, member)

    tar.seek(0)

    # Prove that we are passing encoding all the way down to the TarFile() used
    # for extraction.
    stream = package_streaming.stream_conda_component(
        "package.tar.bz2", tar, component="pkg", encoding="latin-1"
    )

    for t, member in stream:
        member.name.encode("utf-8")
        print(t, member)
