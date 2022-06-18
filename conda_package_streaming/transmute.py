"""
Convert .tar.bz2 to .conda without writing temporary tarfiles to disk.
"""

import contextlib
import io
import json
import os
import tarfile
import time
import zipfile

import zstandard

# streams everything in .tar.bz2 mode
from .package_streaming import stream_conda_component

# increase to reduce speed and increase compression (22 = conda's default)
ZSTD_COMPRESS_LEVEL = 22
# increase to reduce compression and increase speed
ZSTD_COMPRESS_THREADS = 1


@contextlib.contextmanager
def timeme(message: str = ""):
    begin = time.time()
    yield
    end = time.time()
    print(f"{message}{end-begin:0.2f}s")


def test():
    import glob

    conda_packages = []
    tarbz_packages = glob.glob(
        os.path.expanduser("~/miniconda3/pkgs/python-3.8.10-h0e5c897_0_cpython.tar.bz2")
    )

    for packages in (conda_packages, tarbz_packages):
        for package in packages:
            with timeme(f"{package} took "):
                transmute(package)


def transmute(package):
    assert package.endswith(".tar.bz2"), "can only convert .tar.bz2 to .conda"
    file_id = os.path.basename(package)[: -len(".tar.bz2")]

    # x to not append to existing
    conda_file = zipfile.ZipFile(
        f"/tmp/{file_id}.conda", "x", compresslevel=zipfile.ZIP_STORED
    )

    info_compress = zstandard.ZstdCompressor(
        level=ZSTD_COMPRESS_LEVEL, threads=ZSTD_COMPRESS_THREADS
    )
    data_compress = zstandard.ZstdCompressor(
        level=ZSTD_COMPRESS_LEVEL, threads=ZSTD_COMPRESS_THREADS
    )

    # in theory, info_tar could grow uncomfortably big, in which case we would
    # rather swap it to disk
    info_io = io.BytesIO()
    info_stream = info_compress.stream_writer(info_io, closefd=False)
    info_tar = tarfile.TarFile(fileobj=info_stream, mode="w")

    conda_file.writestr("metadata.json", json.dumps({"conda_pkg_format_version": 2}))

    with conda_file.open(f"pkg-{file_id}.tar.zst", "w") as pkg_file:
        pkg_stream = data_compress.stream_writer(pkg_file, closefd=False)
        pkg_tar = tarfile.TarFile(fileobj=pkg_stream, mode="w")

        stream = iter(stream_conda_component(package, None, "pkg"))
        for tar, member in stream:
            tar_get = info_tar if member.name.startswith("info/") else pkg_tar
            if member.isfile():
                tar_get.addfile(member, tar.extractfile(member))
            else:
                tar_get.addfile(member)

        pkg_tar.close()
        pkg_stream.close()

        info_tar.close()
        info_stream.close()

    with conda_file.open(f"info-{file_id}.tar.zst", "w") as info_file:
        info_file.write(info_io.getvalue())


if __name__ == "__main__":
    test()
