import io
import os
import stat
import tarfile
from errno import ELOOP
from pathlib import Path

import pytest

from conda_package_streaming import exceptions, extract, package_streaming

HAS_TAR_FILTER = hasattr(tarfile, "tar_filter")
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


def empty_tarfile(name, mode=0o644, tar_mode="w", create_subdir=False):
    """
    Return BytesIO containing a tarfile with one empty file named :name
    """
    tar = io.BytesIO()
    t = tarfile.open(mode=tar_mode, fileobj=tar)
    if create_subdir:
        tarinfo = tarfile.TarInfo(name=name)
        # Add execute bit for directory
        tarinfo.mode = mode | 0o111
        tarinfo.type = tarfile.DIRTYPE
        t.addfile(tarinfo, io.BytesIO())
        tarinfo = tarfile.TarInfo(name=str(Path(name, name)))
        tarinfo.mode = mode
        t.addfile(tarinfo, io.BytesIO())
    else:
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


@pytest.mark.parametrize(
    "tar_filter",
    (pytest.param(None, id="no tar filter"), pytest.param("data", id="data_filter")),
)
def test_umask(tmp_path, mocker, tar_filter):
    """
    Demonstrate that umask-respecting tar implementation works.

    Mock umask in case it is different on your system.
    """
    if tar_filter is not None and not HAS_TAR_FILTER:
        pytest.skip("Requires tar_filter")
    try:
        MOCK_UMASK = 0o022
        current_umask = os.umask(MOCK_UMASK)
        mocker.patch("conda_package_streaming.package_streaming.UMASK", new=MOCK_UMASK)

        assert (
            package_streaming.TarfileNoSameOwner(
                fileobj=empty_tarfile("file.txt")
            ).umask
            == MOCK_UMASK
        )

        # [
        #   ('S_IFREG', 32768),
        #   ('UF_HIDDEN', 32768),
        #   ('FILE_ATTRIBUTE_INTEGRITY_STREAM', 32768)
        # ]

        # Of the high bits 100755 highest bit 1 can mean just "is regular file"

        name = "naughty_umask"
        tar3 = empty_tarfile(name=name, mode=0o777, create_subdir=True)

        stat_check = stat.S_IRGRP
        stat_name = "S_IRGRP"

        root_path = tmp_path / "stdlib"
        root_path.mkdir()
        files_to_check = [root_path / name, root_path / name / name]

        extract.extract_stream(stream_stdlib(tar3), root_path, tar_filter=tar_filter)
        for file in files_to_check:
            mode = file.stat().st_mode
            # is the new .extractall(filter=) erasing "stat_name"?
            assert mode & stat_check, f"{file} has {stat_name}? %o != %o" % (
                mode,
                mode & stat_check,
            )

        # specifically forbid that stat bit
        MOCK_UMASK |= stat_check
        mocker.patch("conda_package_streaming.package_streaming.UMASK", new=MOCK_UMASK)
        os.umask(MOCK_UMASK)

        root_path = tmp_path / "cps"
        root_path.mkdir()
        files_to_check = [root_path / name, root_path / name / name]

        tar3.seek(0)
        extract.extract_stream(stream(tar3), root_path, tar_filter=tar_filter)
        for file in files_to_check:
            mode = file.stat().st_mode
            if mode & stat_check:
                assert not (mode & stat_check), (
                    f"{file}: No {stat_name} due to umask? %o != %o"
                    % (
                        mode,
                        mode & stat_check,
                    )
                )
    finally:
        os.umask(current_umask)


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
