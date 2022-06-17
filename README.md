# conda-package-streaming

Download conda metadata from packages without transferring entire file.

Uses enhanced pip `lazy_wheel` to fetch a file out of `.conda` with 2 or no more
than 3 range requests.

Uses `tar = tarfile.open(fileobj=response.raw, mode="r|bz2")` to stream remote
`.tar.bz2`. Closes the HTTP request once desired files have been seen.

Experimental.

Could be used to get metadata from local `.tar.bz2` without reading entire file?

# Package goals

* Extract conda packages (both formats)
* Easy to install from pypi or conda
* Do the least amount of I/O possible (no temporary files, transfer partial packages)
* Open files from the network CDN / standard HTTP / s3

* Continue using conda-package-handling to create .conda packages
* Possibly merge into conda-package-handling when this package is mature

# API

```
from conda_package_streaming.fetch_metadata import fetch_meta

# put "info/index.json", "info/recipe/meta.yaml" in destdir
# for .conda, extract entire `info-` into destdir
fetch_meta(url, destdir)
```

# TODO

* s3 support via https://github.com/DavidMuller/aws-requests-auth/blob/master/aws_requests_auth ?
* Or an adapter to issue the necessary s3 get / range requests with either boto3 or requests
* Probably the best Python zstd binding https://github.com/indygreg/python-zstandard

# Generating documentation

Uses markdown, furo theme. Requires newer mdit-py-plugins.

`pip install mdit-py-plugins\>=0.3.0`

`sphinx-apidoc -o docs .`