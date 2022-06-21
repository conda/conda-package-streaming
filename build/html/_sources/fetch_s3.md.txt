fetch\_s3 module
======================

fetch_s3 adapts a s3 client, bucket name, and key to `LazyConda`, or, for
`.tar.bz2`, a normal streaming `GET` request that can be closed before
transferring the whole file.

```{eval-rst}
.. automodule:: conda_package_streaming.fetch_s3
   :members:
   :undoc-members:
   :show-inheritance:
```
