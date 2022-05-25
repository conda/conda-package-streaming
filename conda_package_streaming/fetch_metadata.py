"""
Fetch metadata from remote .conda or .tar.bz2 package.

Try to fetch less than the whole file if possible.

Zip (.conda) is made for this:
When pip's lazy http implementation is modified to print request headers:

$ python -m metayaml.fetch_metadata
https://repo.anaconda.com/pkgs/main/linux-64/absl-py-0.1.10-py27_0.conda fetch
range {'Accept-Encoding': 'identity', 'Range': 'bytes=122880-128735'}, fetch
range {'Accept-Encoding': 'identity', 'Range': 'bytes=118496-122879'}, fetch
range {'Accept-Encoding': 'identity', 'Range': 'bytes=0-10239'}, fetch range
{'Accept-Encoding': 'identity', 'Range': 'bytes=10240-10269'}, fetch range
{'Accept-Encoding': 'identity', 'Range': 'bytes=10270-10303'}

Extracts entire info folder. Appears not to do the bytes-from-end
optimization.

Once you have the index, it would be possible to fetch everything else you want
in a single (compound?) Range request.

How does the charge per-GET-Request compare to the bandwidth saved?


Older format

bzip2 has a very large block size, and we don't know if the info/ directory
is finished early. However if we only want certain files from info/ we can stop
after we've seen them all. Fetching repodata and calling response.raw.tell()
after each tar member:

$ python -m metayaml.fetch_metadata \
    https://repo.anaconda.com/pkgs/main/linux-64/absl-py-0.1.10-py27_0.tar.bz2
128948 info/hash_input.json
128948 info/index.json
128948 info/files
128948 info/about.json
128948 info/paths.json
128948 info/LICENSE.txt
128948 info/git
128948 lib/python2.7/site-packages/absl_py-0.1.10-py2.7.egg-info/dependency_links.txt
128948 lib/python2.7/site-packages/absl_py-0.1.10-py2.7.egg-info/requires.txt
128948 lib/python2.7/site-packages/absl_py-0.1.10-py2.7.egg-info/top_level.txt
128948 lib/python2.7/site-packages/absl/__init__.pyc
128948 lib/python2.7/site-packages/absl/testing/__init__.pyc
128948 info/test/run_test.py
...

A larger package:
$ python -m metayaml.fetch_metadata \
    https://repo.anaconda.com/pkgs/main/linux-64/airflow-1.10.10-py36_0.tar.bz2
286720 info/hash_input.json
286720 info/has_prefix
286720 info/index.json
286720 info/about.json
286720 info/git
286720 info/files
286720 info/paths.json
286720 lib/python3.6/site-packages/airflow/alembic.ini
286720 lib/python3.6/site-packages/airflow/www/templates/airflow/variables/README.md
...
286720 info/test/test_time_dependencies.json
...
634880 lib/python3.6/site-packages/airflow/www/static/ace.js
634880 bin/airflow
"""

import logging
import sys
import urllib.parse
import zipfile
from pathlib import Path

import requests

# Excellent HTTP Range request file-like object
from . import lazy_wheel, package_streaming

log = logging.getLogger(__name__)

session = requests.Session()
session.headers["User-Agent"] = "conda-package-streaming/0.1.0"


class LazyConda(lazy_wheel.LazyZipOverHTTP):
    def prefetch(self, conda_file_id):
        """
        Conda fork specific. Prefetch the `.info` range from the remote archive.
        Reduces number of Range requests to 2 or 3 (1 or 2 for the directory, 1
        for the file).

        conda_file_id: name of .conda without path or `.conda` extension
        """
        target_file = f"info-{conda_file_id}.tar.zst"
        with self._stay():  # not strictly necessary
            # try to read entire conda info in one request
            zf = zipfile.ZipFile(self)
            infolist = zf.infolist()
            for i, info in enumerate(infolist):
                if info.filename == target_file:
                    start = info.header_offset
                    try:
                        end = infolist[i + 1].header_offset
                    except IndexError:
                        end = zf.start_dir
                    self.seek(start)
                    self.read(end - start)
                    log.debug(
                        "prefetch %s-%s",
                        info.header_offset,
                        end,
                    )
                    break
            else:
                log.debug("no zip prefetch")


def stream_meta(url):
    """
    Yield (tar, member) for conda package at url

    Just "info/" for .conda, all members for tar.
    """
    parsed_url = urllib.parse.urlparse(url)
    _, filename = parsed_url.path.rsplit("/", 1)
    if filename.endswith(".conda"):
        file_id, _ = filename.rsplit(".", 1)
        conda = LazyConda(url, session)
        conda.prefetch(file_id)
    elif filename.endswith(".tar.bz2"):
        response = requests.get(url, stream=True)
        conda = response.raw
    else:
        raise ValueError("Unsupported extension %s", url)

    return package_streaming.stream_conda_info(filename, conda)


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


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    fetch_meta(sys.argv[1], Path("/tmp/info").absolute())
