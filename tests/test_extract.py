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
        def extractall(self, path=None, members=None, filter=None):
            raise OSError(ELOOP, "case sensitivity")

    class TarOSError(tarfile.TarFile):
        def extractall(self, path=None, members=None, filter=None):
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

    # If we are using tarfile.filter, the leading / will be stripped instead.
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
    MOCK_UMASK = 0o022
    mocker.patch("conda_package_streaming.package_streaming.UMASK", new=MOCK_UMASK)

    assert (
        package_streaming.TarfileNoSameOwner(fileobj=empty_tarfile("file.txt")).umask
        == MOCK_UMASK
    )

    # [('S_IFREG', 32768), ('UF_HIDDEN', 32768), ('FILE_ATTRIBUTE_INTEGRITY_STREAM', 32768)]

    # Of the high bits 100755 highest bit 1 can mean just "is regular file"

    tar3 = empty_tarfile(name="naughty_umask", mode=0o777)

    stat_check = stat.S_IRGRP
    stat_name = "S_IRGRP"

    extract.extract_stream(stream_stdlib(tar3), tmp_path)
    mode = (tmp_path / "naughty_umask").stat().st_mode
    # is the new .extractall(filter=) erasing group-writable?
    assert mode & stat.S_IRGRP, f"Has {stat_name}? %o != %o" % (
        mode,
        mode & stat_check,
    )

    # specifically forbid that stat bit
    MOCK_UMASK |= stat_check
    mocker.patch("conda_package_streaming.package_streaming.UMASK", new=MOCK_UMASK)

    tar3.seek(0)
    extract.extract_stream(stream(tar3), tmp_path)
    mode = (tmp_path / "naughty_umask").stat().st_mode
    assert not mode & stat_check, f"No {stat_name} due to umask? %o != %o" % (
        mode,
        mode & stat_check,
    )


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
