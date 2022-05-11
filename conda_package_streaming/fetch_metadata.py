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
import tarfile
import zipfile
from pathlib import Path

import requests
from conda_package_handling import conda_fmt

# Excellent HTTP Range request file-like object
from . import lazy_wheel

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


def fetch_tarbz(url, destdir, checklist=set()):
    """
    Stream url, stop when all files in set checklist (file names like
    info/recipe/meta.yaml) have been found.
    """
    response = requests.get(url, stream=True)
    tar = tarfile.open(fileobj=response.raw, mode="r|bz2")
    for member in tar:
        if member.name in checklist:
            tar.extract(member, destdir)
            checklist.remove(member.name)
        if not checklist:
            break
    log.debug(
        f"tell {response.raw.tell():,} content-length {int(response.headers['Content-Length']):,}",
    )
    response.close()


def fetch_conda(url, destdir):
    """
    Extract whole .conda info/ into destdir/info.

    Fetch only bytes ranges of url.
    """
    # filename without path or .conda extension
    file_id = url.split("/")[-1].rsplit(".", 1)[0]
    conda = LazyConda(url, session)
    conda.prefetch(file_id)
    conda_fmt._extract_component(conda, file_id, "info", str(destdir))
    if conda._request_count > 3:
        log.warn("Should take 3 or fewer requests but took %d", conda._request_count)


def fetch_meta(url, destdir):
    if url.endswith(".tar.bz2"):
        fetch_tarbz(
            url, destdir, checklist={"info/index.json", "info/recipe/meta.yaml"}
        )
    elif url.endswith(".conda"):
        fetch_conda(url, destdir)
    else:
        raise ValueError("Unsupported extension %s", url)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    fetch_meta(sys.argv[1], Path("/tmp/info").absolute())
