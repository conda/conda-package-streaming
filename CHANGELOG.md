[//]: # (current developments)

## 0.10.0 (2024-05)
* Use zip64 extensions when converting .tar.bz2 to .conda, if uncompressed size
  is close to the 2GB ZIP64_LIMIT. (#79)

## 0.9.0 (2023-07)

* Respect umask when extracting files. [#65](https://github.com/conda/conda-package-streaming/pulls/65); [conda issue #12829](https://github.com/conda/conda/issues/12829).

## 0.8.0 (2023-05)

* Update transmute to use SpooledTemporaryFile instead of streaming directly to
  zip [(#57)](https://github.com/conda/conda-package-streaming/issues/57). This
  can reduce zstd memory usage during decompression.
* `transmute` returns Path to transmuted package instead of `None`.
