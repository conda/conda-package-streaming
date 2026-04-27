"""
Convert .tar.bz2 to .conda

Uses ``tempfile.SpooledTemporaryFile`` to buffer ``pkg-*.tar`` and
``info-*.tar``, then compress directly into an open `ZipFile` at the end.
`SpooledTemporaryFile` buffers the first 10MB of the package and its metadata in
memory, but writes out to disk for larger packages.
"""

from __future__ import annotations

import os
import tarfile
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from .create import ZSTD_COMPRESS_LEVEL, ZSTD_COMPRESS_THREADS, conda_builder

# streams everything in .tar.bz2 mode
from .package_streaming import CondaComponent, stream_conda_component

if TYPE_CHECKING:
    from collections.abc import Callable

    from .create import LegacyCompressorOrFactory


def transmute(
    package,
    path,
    *,
    compressor: LegacyCompressorOrFactory | None = None,
    compression_level: int = ZSTD_COMPRESS_LEVEL,
    compression_threads: int = ZSTD_COMPRESS_THREADS,
    is_info: Callable[[str], bool] = lambda filename: filename.startswith("info/"),
) -> Path:
    """
    Convert .tar.bz2 conda package to .conda-format under path.

    :param package: path to .tar.bz2 conda package
    :param path: destination path for transmuted .conda package
    :param compressor: Optional legacy ``zstandard`` compressor object (or
        factory returning one) with ``stream_writer(...)``.
    :param compression_level: zstd compression level for ``compression.zstd`` or
        ``backports.zstd`` code path.
    :param compression_threads: Number of zstd worker threads for
        ``compression.zstd`` or ``backports.zstd`` code path.
    :param is_info: A function that returns True if a file belongs in the
        ``info`` component of a `.conda` package.  ``conda-package-handling``
        (not this package ``conda-package-streaming``) uses a set of regular
        expressions to keep expected items in the info- component, while other
        items starting with ``info/`` wind up in the pkg- component.

    :return: Path to transmuted package.
    """
    assert package.endswith(".tar.bz2"), "can only convert .tar.bz2 to .conda"
    assert os.path.isdir(path)
    stem = os.path.basename(package)[: -len(".tar.bz2")]
    package_stream = stream_conda_component(package)

    return transmute_stream(
        stem,
        path,
        compressor=compressor,
        compression_level=compression_level,
        compression_threads=compression_threads,
        is_info=is_info,
        package_stream=package_stream,
    )


def transmute_stream(
    stem,
    path,
    *,
    compressor: LegacyCompressorOrFactory | None = None,
    compression_level: int = ZSTD_COMPRESS_LEVEL,
    compression_threads: int = ZSTD_COMPRESS_THREADS,
    is_info: Callable[[str], bool] = lambda filename: filename.startswith("info/"),
    package_stream: Iterator[tuple[tarfile.TarFile, tarfile.TarInfo]],
):
    """
    Convert (TarFile, TarInfo) iterator like those produced by
    ``stream_conda_component`` to .conda-format under path. Allows for more
    creative data sources.

    e.g. recompress ``.conda``:

    .. code-block:: python

        transmute_stream(
            ...,
            package_stream=itertools.chain(
                stream_conda_component("package.conda", component=CondaComponent.pkg),
                stream_conda_component("package.conda", component=CondaComponent.info),
            ),
        )

    This example could move files between the ``pkg-`` and ``info-`` components
    depending on the ``is_info`` function.

    :param stem: output filename without extension
    :param path: destination path for transmuted .conda package
    :param compressor: Optional legacy ``zstandard`` compressor object (or
        factory returning one) with ``stream_writer(...)``.
    :param compression_level: zstd compression level for ``compression.zstd`` or
        ``backports.zstd`` code path.
    :param compression_threads: Number of zstd worker threads for
        ``compression.zstd`` or ``backports.zstd`` code path.
    :param is_info: A function that returns True if a file belongs in the
        ``info`` component of a `.conda` package.  ``conda-package-handling``
        (not this package ``conda-package-streaming``) uses a set of regular
        expressions to keep expected items in the info- component, while other
        items starting with ``info/`` wind up in the pkg- component.
    :param package_stream: Iterator of (Tarfile, TarInfo) tuples.

    :return: Path to transmuted package.
    """
    output_path = Path(path, f"{stem}.conda")
    with conda_builder(
        stem,
        path,
        compressor=compressor,
        compression_level=compression_level,
        compression_threads=compression_threads,
        is_info=is_info,
    ) as conda_tar:
        for tar, member in package_stream:
            if member.isfile():
                conda_tar.addfile(member, tar.extractfile(member))
            else:
                conda_tar.addfile(member)

    return output_path


def transmute_tar_bz2(
    package: str,
    path,
) -> Path:
    """
    Convert .conda package to .tar.bz2 format under path.

    Can recompress .tar.bz2 packages.

    Args:
        package: path to .conda or .tar.bz2 package.
        path: destination path for transmuted package.

    Returns:
        Path to transmuted package.
    """
    assert package.endswith((".tar.bz2", ".conda")), "Unknown extension"
    assert os.path.isdir(path)

    incoming_format = ".conda" if package.endswith(".conda") else ".tar.bz2"

    file_id = os.path.basename(package)[: -len(incoming_format)]

    if incoming_format == ".conda":
        # .tar.bz2 MUST place info/ first.
        components = [CondaComponent.info, CondaComponent.pkg]
    else:
        # .tar.bz2 doesn't filter by component
        components = [CondaComponent.pkg]

    output_path = Path(path, f"{file_id}.tar.bz2")

    with open(package, "rb") as fileobj, tarfile.open(output_path, "x:bz2") as pkg_tar:
        for component in components:
            stream = iter(stream_conda_component(package, fileobj, component=component))
            for tar, member in stream:
                if member.isfile():
                    pkg_tar.addfile(member, tar.extractfile(member))
                else:
                    pkg_tar.addfile(member)

    return output_path
