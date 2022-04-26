# conda-package-streaming

Download conda metadata from packages without transferring entire file.

Uses enhanced pip `lazy_wheel` to fetch a file out of `.conda` with 2 or no more
than 3 range requests.

Uses `tar = tarfile.open(fileobj=response.raw, mode="r|bz2")` to stream remote
`.tar.bz2`. Closes the HTTP request once desired files have been seen.

Experimental.

Could be used to get metadata from local `.tar.bz2` without reading entire file?

# API

```
from conda_package_streaming.fetch_metadata import fetch_meta

# put "info/index.json", "info/recipe/meta.yaml" in destdir
# for .conda, extract entire `info-` into destdir
fetch_meta(url, destdir)
```