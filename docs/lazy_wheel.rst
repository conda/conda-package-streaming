lazy\_wheel module
==================

`lazy_wheel` is derived from pip's wheel download code. It is really a seekable
file-like based on HTTP range requests, backed by a sparse temporary file. ZIP
archives have a directory at the end of the file giving the offset to each
compressed member. We fetch the directory, and then the portion of the file
containing the member or members of interest, for a maximum of 3 requests to
retrieve any individual file in the archive.

.. automodule:: conda_package_streaming.lazy_wheel
   :members:
   :undoc-members:
   :show-inheritance:
