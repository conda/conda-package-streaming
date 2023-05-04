% conda-package-streaming documentation master file, created by
% sphinx-quickstart on Fri Jun 17 14:43:38 2022.
% You can adapt this file completely to your liking, but it should at least
% contain the root `toctree` directive.

# Welcome to conda-package-streaming's documentation!

`conda-package-streaming` strives to be the most efficient way to read from new
and old format `.conda` and `.tar.bz2` [conda
packages](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/packages.html).
`conda-package-streaming` can read from conda packages without ever writing to
disk, unlike
[conda-package-handling](https://github.com/conda/conda-package-handling)
`< 2.0.0`'s temporary directories.
[conda-package-handling](https://github.com/conda/conda-package-handling)
`>= 2.0.0` uses `conda-package-streaming`. This library can also read a package
from a URL or a stream without transferring the entire archive.

`conda-package-streaming` uses the standard library
[`zipfile`](https://docs.python.org/3/library/zipfile.html) and
[`tarfile`](https://docs.python.org/3/library/tarfile.html), and
[`zstandard`](https://github.com/indygreg/python-zstandard) to handle
zstd-compressed streams.


```{include} ../README.md
```

```{toctree}
:caption: 'Contents:'
:maxdepth: 2
modules
changelog
```

# Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
