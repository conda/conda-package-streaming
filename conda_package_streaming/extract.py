"""
Extract package to directory, with checks against tar members extracting outside
the target directory.
"""

from __future__ import annotations

import os
import tarfile
from collections.abc import Generator
from errno import ELOOP
from pathlib import Path

from . import exceptions, package_streaming

__all__ = ["extract_stream", "extract"]
HAS_TAR_FILTER = hasattr(tarfile, "tar_filter")


def extract_stream(
    stream: Generator[tuple[tarfile.TarFile, tarfile.TarInfo]],
    dest_dir: Path | str,
    tar_filter: str | None = None,
):
    """
    Pipe ``stream_conda_component`` output here to extract every member into
    dest_dir.

    For ``.conda`` will need to be called twice (for info and pkg components);
    for ``.tar.bz2`` every member is extracted.
    """
    dest_dir = os.path.realpath(dest_dir)
    dest_dir_with_sep = dest_dir if dest_dir.endswith(os.sep) else dest_dir + os.sep

    # The fast path's safety claim relies on the filesystem tree under
    # ``dest_dir`` containing only paths *we* created — which is only
    # true when ``dest_dir`` was empty when extract started. If a caller
    # hands us a ``dest_dir`` that already contains a symlink, a member
    # whose name traverses through that pre-existing symlink would
    # escape under the string-only check. We do one ``scandir`` call up
    # front; if anything is in there already, we conservatively start
    # the entire stream in fallback mode.
    try:
        with os.scandir(dest_dir) as it:
            dest_dir_was_empty = next(it, None) is None
    except FileNotFoundError:
        # ``extractall`` will create ``dest_dir`` for us.
        dest_dir_was_empty = True
    except OSError:
        # ``dest_dir`` exists but isn't readable as a directory
        # (regular file, permission denied, etc.). Be conservative —
        # take the fallback for the whole stream, and let
        # ``extractall`` surface the canonical error.
        dest_dir_was_empty = False

    # Per-member safety check. Historically this called
    # ``os.path.realpath(os.path.join(dest_dir, name))`` which walks the
    # joined path and issues one ``lstat`` per path component — roughly
    # 15 lstats per member on scientific-Python archives, which works
    # out to the single largest contributor to extract wall time after
    # the raw file I/O.
    #
    # We split the check into a fast path and a fallback. For a member
    # whose name contains no ``..`` and no absolute-path prefix, and
    # while the archive has so far yielded only regular files and
    # directories, a pure string-based ``normpath`` + ``startswith``
    # check is provably equivalent to ``realpath`` — the filesystem
    # tree under ``dest_dir`` contains only paths we created, so no
    # symlinks are there to traverse. Once we encounter a member that
    # is a symlink, hardlink, absolute-path, or ``..``-containing,
    # subsequent members fall back to the full ``realpath`` check
    # because the extracted tree may now contain symlinks that could
    # redirect writes outside ``dest_dir``.
    #
    # Across the full macOS conda-forge package cache (186 archives,
    # 30,299 members, 1,274 symlinks), 81 % of members extract via the
    # fast path and 142 / 186 archives never trigger the fallback. See
    # #175 for the compatibility survey and before/after numbers.
    for tar_file, _ in stream:

        def checked_members():
            seen_risky = not dest_dir_was_empty
            for member in tar_file:
                name = member.name
                if not seen_risky:
                    # In tar, member names are always ``/``-separated
                    # (POSIX 1003.1) and ``tarfile`` exposes them
                    # verbatim, so a single ``split("/")`` is enough
                    # on every platform.
                    if (
                        member.issym()
                        or member.islnk()
                        or name.startswith("/")
                        or name.startswith(os.sep)
                        or ".." in name.split("/")
                    ):
                        seen_risky = True

                if seen_risky:
                    abs_target = os.path.realpath(os.path.join(dest_dir, name))
                    ok = abs_target == dest_dir or abs_target.startswith(
                        dest_dir_with_sep,
                    )
                else:
                    # ``join`` + ``normpath`` are pure string ops, no syscalls.
                    normalized = os.path.normpath(os.path.join(dest_dir, name))
                    ok = normalized == dest_dir or normalized.startswith(
                        dest_dir_with_sep,
                    )

                if not ok:
                    raise exceptions.SafetyError(
                        f"contains unsafe path: {name}",
                    )
                yield member

        try:
            tar_args = {"path": dest_dir, "members": checked_members()}
            if HAS_TAR_FILTER:
                tar_args["filter"] = tar_filter or "fully_trusted"
            tar_file.extractall(**tar_args)
        except OSError as e:
            if e.errno == ELOOP:
                raise exceptions.CaseInsensitiveFileSystemError() from e
            raise

        # next iteration of for loop raises GeneratorExit in stream
        stream.close()


def extract(filename, dest_dir=None, fileobj=None):
    """
    Extract all components of conda package to dest_dir.

    fileobj: must be seekable if provided, if a ``.conda`` package.
    """
    assert dest_dir, "dest_dir is required"
    if str(filename).endswith(".conda"):
        components = [
            package_streaming.CondaComponent.pkg,
            package_streaming.CondaComponent.info,
        ]
    else:  # .tar.bz2 doesn't filter by component
        components = [package_streaming.CondaComponent.pkg]

    closefd = False
    if not fileobj:
        fileobj = open(filename, "rb")
        closefd = True

    try:
        for component in components:
            stream = package_streaming.stream_conda_component(
                filename, fileobj, component=component
            )
            extract_stream(stream, dest_dir)
    finally:
        if closefd:
            fileobj.close()
