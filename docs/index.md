% conda-package-streaming documentation master file, created by
% sphinx-quickstart on Fri Jun 17 14:43:38 2022.
% You can adapt this file completely to your liking, but it should at least
% contain the root `toctree` directive.

# Welcome to conda-package-streaming's documentation!

`conda-package-streaming` strives to be the most efficient way to read from new
and old format `.conda` and `.tar.bz2` Conda packages. `conda-package-streaming`
can read from conda packages without ever writing to disk, unlike
`conda-package-handling`'s temporary directories. It can read a package from a
URL or a stream without transferring the entire archive.

```{toctree}
:caption: 'Contents:'
:maxdepth: 2
modules
```

# Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
