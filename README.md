# conda-package-streaming

Download conda metadata from packages without transferring entire file. Get
metadata from local `.tar.bz2` without reading entire file.

Uses enhanced pip `lazy_wheel` to fetch a file out of `.conda` with no more than
3 range requests, but usually 2.

Uses `tar = tarfile.open(fileobj=...)` to stream remote `.tar.bz2`. Closes the
HTTP request once desired files have been seen.

# Quickstart

The basic API yields (tarfile, member) tuples from conda files as tarfile is
needed to extract member. Note the `.tar.bz2` format yields all members, not
just `info/`, from `stream_conda_info` / `stream_conda_component`, while the
`.conda` format yields members from the requested inner archive — allowing the
caller to decide when to stop reading.

From a url,
```python
from conda_package_streaming import fetch_metadata
# url = (ends with .conda or .tar.bz2)
for tar, member in fetch_metadata.stream_meta(url):
    if member.name == "info/index.json":
        index_json = json.load(tar.extractfile(member))
        break
```

From s3,
```python
client = boto3.client("s3")
from conda_package_streaming import fetch_s3
# key = (ends with .conda or .tar.bz2)
for tar, member in fetch_s3.stream_meta(client, bucket, key):
    if member.name == "info/index.json":
        index_json = json.load(tar.extractfile(member))
        break
```

From a filename,
```python
from conda_package_streaming import package_streaming
# filename = (ends with .conda or .tar.bz2)
for tar, member in package_streaming.stream_conda_info(filename):
    if member.name == "info/index.json":
        index_json = json.load(tar.extractfile(member))
        break
```

From a file-like object,
```python
from contextlib import closing

from conda_package_streaming.fetch_metadata import reader_for_conda_url
from conda_package_streaming.package_streaming import stream_conda_component
filename, conda = reader_for_conda_url(url)

# file object must be seekable for `.conda` format, but merely readable for `.tar.bz2`
with closing(conda):
    for tar, member in stream_conda_component(filename, conda, component="info"):
        if member.name == "info/index.json":
            index_json = json.load(tar.extractfile(member))
            break
```

# Package goals

* Extract conda packages (both formats)
* Easy to install from pypi or conda
* Do the least amount of I/O possible (no temporary files, transfer partial packages)
* Open files from the network / standard HTTP / s3

* Continue using conda-package-handling to create .conda packages

# Generating documentation

Uses markdown, furo theme. Requires newer mdit-py-plugins.

`pip install conda-package-streaming[docs]`

One time:
`sphinx-apidoc -o docs .`