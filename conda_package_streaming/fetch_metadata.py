"""
Fetch metadata from remote .conda or .tar.bz2 package.

Try to fetch less than the whole file if possible.
"""

import logging
import sys
import urllib.parse
from contextlib import closing
from pathlib import Path

import requests

from . import package_streaming

# Excellent HTTP Range request file-like object
from .lazy_wheel import LazyConda

log = logging.getLogger(__name__)

session = requests.Session()
session.headers["User-Agent"] = "conda-package-streaming/0.1.0"


def fetch_meta(url, destdir):
    """
    Extract info/index.json and info/recipe.meta.yaml from url to destdir; close
    url as soon as those files are found.
    """
    checklist = {"info/index.json", "info/recipe/meta.yaml"}
    stream = stream_meta(url)
    for (tar, member) in stream:
        if member.name in checklist:
            tar.extract(member, destdir)
            checklist.remove(member.name)
        if not checklist:
            stream.close()
            break


def stream_meta(url):
    """
    Yield (tar, member) for conda package at url

    Just "info/" for .conda, all members for tar.
    """
    filename, conda = reader_for_conda_url(url)

    with closing(conda):
        yield from package_streaming.stream_conda_info(filename, conda)


def reader_for_conda_url(url):
    """
    Return (name, file_like) suitable for package_streaming APIs
    """
    parsed_url = urllib.parse.urlparse(url)
    *_, filename = parsed_url.path.rsplit("/", 1)
    if filename.endswith(".conda"):
        file_id, _ = filename.rsplit(".", 1)
        conda = LazyConda(url, session)
        conda.prefetch(file_id)
    elif filename.endswith(".tar.bz2"):
        response = requests.get(url, stream=True)
        conda = response.raw
    else:
        raise ValueError("Unsupported extension %s", url)
    return filename, conda


if __name__ == "__main__":  # pragma nocover
    import logging

    logging.basicConfig(level=logging.DEBUG)
    fetch_meta(sys.argv[1], Path(sys.argv[2]).absolute())
