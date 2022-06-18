"""
Convert .tar.bz2 to .conda without temporary files.

Streams main `pkg-*` `.tar.zst` into open `ZipFile`, while buffering `info-*`
`.tar.zst` in memory, writing it out at the end.

Works well for a typical ~10k `info-*`, but the conda format does not guarantee
a small `info-*`.

Conda packages created this way will also have `info-*` as the last element in
the `ZipFile`, instead of the first for normal conda packages.
"""

import io
import json
import os
import tarfile
import zipfile

import zstandard

# streams everything in .tar.bz2 mode
from .package_streaming import stream_conda_component

# increase to reduce speed and increase compression (22 = conda's default)
ZSTD_COMPRESS_LEVEL = 22
# increase to reduce compression and increase speed
ZSTD_COMPRESS_THREADS = 1


def transmute(
    package,
    path,
    *,
    compressor=lambda: zstandard.ZstdCompressor(
        level=ZSTD_COMPRESS_LEVEL, threads=ZSTD_COMPRESS_THREADS
    ),
):
    """
    Convert .tar.bz2 conda :package to .conda-format under path.

    :param package: path to .tar.bz2 conda package
    :param path: destination path for transmuted .conda package
    :param compressor: A function that creates instances of
        ``zstandard.ZstdCompressor()`` to override defaults.
    """
    assert package.endswith(".tar.bz2"), "can only convert .tar.bz2 to .conda"
    assert os.path.isdir(path)
    file_id = os.path.basename(package)[: -len(".tar.bz2")]

    # x to not append to existing
    conda_file = zipfile.ZipFile(
        os.path.join(path, f"{file_id}.conda"), "x", compresslevel=zipfile.ZIP_STORED
    )

    info_compress = compressor()
    data_compress = compressor()

    # in theory, info_tar could grow uncomfortably big, in which case we would
    # rather swap it to disk
    info_io = io.BytesIO()
    info_stream = info_compress.stream_writer(info_io, closefd=False)
    info_tar = tarfile.TarFile(fileobj=info_stream, mode="w")

    conda_file.writestr("metadata.json", json.dumps({"conda_pkg_format_version": 2}))

    with conda_file.open(f"pkg-{file_id}.tar.zst", "w") as pkg_file:
        pkg_stream = data_compress.stream_writer(pkg_file, closefd=False)
        pkg_tar = tarfile.TarFile(fileobj=pkg_stream, mode="w")

        stream = iter(stream_conda_component(package))
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
