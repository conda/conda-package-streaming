import contextlib
import io
import itertools
import os
import tarfile
import time
from pathlib import Path
from zipfile import ZipFile

import pytest
import zstandard
from conda_package_handling.validate import validate_converted_files_match_streaming

from conda_package_streaming.create import anonymize
from conda_package_streaming.package_streaming import (
    CondaComponent,
    stream_conda_component,
)
from conda_package_streaming.transmute import (
    transmute,
    transmute_stream,
    transmute_tar_bz2,
)


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


def test_transmute(conda_paths: list[Path], tmpdir):
    tarbz_packages = []
    for path in conda_paths:
        path = str(path)
        if path.endswith(".tar.bz2") and (1 << 20 < os.stat(path).st_size < 1 << 22):
            tarbz_packages = [path]
    conda_packages = []  # not supported

    assert tarbz_packages, "no medium-sized .tar.bz2 packages found"

    metadata_checks = 0

    for packages in (conda_packages, tarbz_packages):
        for package in packages:
            with timeme(f"{package} took "):
                out = transmute(package, tmpdir)
                _, missing, mismatched = validate_converted_files_match_streaming(
                    out, package, strict=True
                )
                assert missing == mismatched == []
                if out.name.endswith(".conda"):
                    with ZipFile(out) as zf:
                        metadata_checks += 1
                        assert "metadata.json" in zf.namelist()

    assert metadata_checks > 0


def test_transmute_symlink(tmpdir, testtar_bytes):
    testtar = Path(tmpdir, "test.tar.bz2")
    testtar.write_bytes(testtar_bytes)

    out = transmute(str(testtar), tmpdir)
    _, missing, mismatched = validate_converted_files_match_streaming(
        out, testtar, strict=True
    )
    assert missing == mismatched == []


def test_transmute_info_filter(tmpdir, testtar_bytes):
    testtar = Path(tmpdir, "test.tar.bz2")
    testtar.write_bytes(testtar_bytes)

    transmute(
        str(testtar), tmpdir, is_info=lambda filename: filename == "info/expected"
    )

    with open(Path(tmpdir, "test.conda"), "rb") as fileobj:
        for component, expected in (
            (CondaComponent.info, {"info/expected"}),
            (
                CondaComponent.pkg,
                {
                    "info/unexpected",
                    "symlink",
                },
            ),
        ):
            items = stream_conda_component("test.conda", fileobj, component)
            assert {member.name for tar, member in items} == expected, items


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
                out = transmute_tar_bz2(package, tmpdir)
                _, missing, mismatched = validate_converted_files_match_streaming(
                    out, package, strict=True
                )
                assert missing == mismatched == []


def test_transmute_tarbz2_to_tarbz2(tmpdir, testtar_bytes):
    testtar = Path(tmpdir, "test.tar.bz2")
    testtar.write_bytes(testtar_bytes)
    outdir = Path(tmpdir, "output")
    outdir.mkdir()
    out = transmute_tar_bz2(str(testtar), outdir)
    _, missing, mismatched = validate_converted_files_match_streaming(
        out, testtar, strict=True
    )
    assert missing == mismatched == []


def test_transmute_conditional_zip64(tmp_path, mocker):
    """
    Test that zip64 is used in transmute after a threshold.
    """

    LIMIT = 16384

    for test_size, extra_expected in (LIMIT // 2, False), (LIMIT * 2, True):
        mocker.patch("conda_package_streaming.create.CONDA_ZIP64_LIMIT", new=LIMIT)
        mocker.patch("zipfile.ZIP64_LIMIT", new=LIMIT)

        tmp_tar = tmp_path / f"{test_size}.tar.bz2"
        with tarfile.open(tmp_tar, "w:bz2") as tar:
            pkg = tarfile.TarInfo(name="packagedata")
            data = io.BytesIO(os.urandom(test_size))
            pkg.size = len(data.getbuffer())
            tar.addfile(pkg, data)

            info = tarfile.TarInfo(name="info/data")
            data = io.BytesIO(os.urandom(test_size))
            info.size = len(data.getbuffer())
            tar.addfile(info, data)

        out = transmute(str(tmp_tar), tmp_path)

        with ZipFile(out) as e:
            assert e.filelist[0].extra == b""
            # when zip64 extension is used, extra contains zip64 headers
            assert bool(e.filelist[1].extra) == extra_expected
            assert bool(e.filelist[2].extra) == extra_expected


def test_transmute_stream(tmpdir, conda_paths):
    """
    Test example from transmute_stream documentation. Recompress .conda using
    transmute_stream()
    """
    conda_packages = []
    for path in conda_paths:
        if path.name.endswith(".conda") and (1 << 20 < os.stat(path).st_size < 1 << 22):
            conda_packages.append(path)

    for package in conda_packages[:3]:
        file_id = package.name

        transmute_stream(
            file_id,
            tmpdir,
            compressor=lambda: zstandard.ZstdCompressor(),
            package_stream=itertools.chain(
                stream_conda_component(package, component=CondaComponent.pkg),
                stream_conda_component(package, component=CondaComponent.info),
            ),
        )


def test_anonymize_helper():
    ti = tarfile.TarInfo(name="info")
    ti.uid = ti.gid = 500
    ti.uname = ti.gname = "somebody"
    anon = anonymize(ti)
    assert anon.name == ti.name  # they are also the same object
    assert anon.uid == anon.gid == 0
    assert anon.uname == anon.gname == ""
