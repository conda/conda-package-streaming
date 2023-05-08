[//]: # (current developments)

## 0.8.0 (2023-05)

* Update transmute to use SpooledTemporaryFile instead of streaming directly to
  zip [(#57)](https://github.com/conda/conda-package-streaming/issues/57). This
  can reduce zstd memory usage during decompression.
* `transmute` returns Path to transmuted package instead of `None`.
