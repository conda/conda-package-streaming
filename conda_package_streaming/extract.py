"""
Extract package to directory, with checks against tar members extracting outside
the target directory.
"""

import os
import sys
import tarfile
from errno import ELOOP
from pathlib import Path
from typing import Generator, Tuple

from . import exceptions, package_streaming

__all__ = ["extract_stream", "extract"]


def extract_stream(
    stream: Generator[Tuple[tarfile.TarFile, tarfile.TarInfo], None, None],
    dest_dir: Path | str,
):
    """
    Pipe ``stream_conda_component`` output here to extract every member into
    dest_dir.

    For ``.conda`` will need to be called twice (for info and pkg components);
    for ``.tar.bz2`` every member is extracted.
    """
    dest_dir = str(dest_dir)
    # we don't extract to cwd; only used to check that tar member does not
    # escape its target directory:
    cwd = os.getcwd()

    for tar_file, _ in stream:

        # careful not to seek backwards
        def checked_members():
            # from conda_package_handling
            for member in tar_file:
                if os.path.isabs(member.name) or not os.path.realpath(
                    member.name
                ).startswith(cwd):
                    raise exceptions.InvalidArchiveError(
                        "contains unsafe path: {} {}".format(
                            os.path.realpath(member.name), cwd
                        ),
                    )
                yield member

        try:
            tar_file.extractall(path=dest_dir, members=checked_members())
        except OSError as e:
            if e.errno == ELOOP:
                raise exceptions.CaseInsensitiveFileSystemError() from e
            raise

        # next iteraton of for loop raises GeneratorExit in stream
        stream.close()

    if sys.platform.startswith("linux") and os.getuid() == 0:
        # When extracting as root, tarfile will by restore ownership
        # of extracted files.  However, we want root to be the owner
        # (our implementation of --no-same-owner).

        # XXX we could only chown collected names from checked_members()
        for root, _, files in os.walk(dest_dir):
            for fn in files:
                p = os.path.join(root, fn)
                os.lchown(p, 0, 0)


def extract(filename, dest_dir=None, fileobj=None):
    """
    Extract all components of conda package to dest_dir.

    fileobj: must be seekable if provided, if a ``.conda`` package.
    """
    assert dest_dir, "dest_dir is required"
    if str(filename).endswith(".conda"):
        components = list(package_streaming.CondaComponent)
    else:  # .tar.bz2 doesn't filter by component
        components = [package_streaming.CondaComponent.pkg]

    if not fileobj:
        fileobj = open(filename, "rb")

    for component in components:
        stream = package_streaming.stream_conda_component(
            filename, fileobj, component=component
        )
        extract_stream(stream, dest_dir)
