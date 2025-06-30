[//]: # (current developments)

## 0.12.0 (2025-06)

* Skip setting permissions if `tarinfo.mode` is `None`. (#140)
* Set minimum Python version to 3.9. (#142)
* Add flag to deal with package servers that reply `416 Range Not
  Satisfiable` if requested range is larger than entire file, when
  using lazy
  [`conda_reader_for_url`](https://conda.github.io/conda-package-streaming/url.html#conda_package_streaming.url.conda_reader_for_url).
  (#132)
* Format with Ruff (#133)

## 0.11.0 (2024-10)

* Add Python 3.12 to test matrix.
* Pass Python `tarfile.extractall(filter="fully_trusted")` in addition to
  internal filtering, when available, to avoid Python 3.12+ `DeprecationWarning`
  (#87)
* Improve umask handling. (#106)
* Add `transmute_stream(...)` to create `.conda` from `(TarFile, TarInfo)`. (#90)
  iterators, allowing more creative data sources than just `.tar.bz2` inputs.
* Add `create` module with `TarFile` interface for creating `.conda`
  archives, also used by `transmute`. (#90)
* Pass `encoding="utf-8"` to `TarFile` instead of the system default, avoiding
  rare potential issues with non-ASCII filenames. (#93)

## 0.10.0 (2024-06)

* Use zip64 extensions when converting .tar.bz2 to .conda, if uncompressed size
  is close to the 2GB ZIP64_LIMIT. (#79)

## 0.9.0 (2023-07)

* Respect umask when extracting files. [#65](https://github.com/conda/conda-package-streaming/pulls/65); [conda issue #12829](https://github.com/conda/conda/issues/12829).

## 0.8.0 (2023-05)

* Update transmute to use SpooledTemporaryFile instead of streaming directly to
  zip [(#57)](https://github.com/conda/conda-package-streaming/issues/57). This
  can reduce zstd memory usage during decompression.
* `transmute` returns Path to transmuted package instead of `None`.
