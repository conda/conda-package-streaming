# conda_package_streaming

Fetch metadata from remote .conda or .tar.bz2 package.

Try to fetch less than the whole file if possible.

Zip (.conda) is made for this:
When pip's lazy http implementation is modified to print request headers:

```
$ python -m metayaml.fetch_metadata
https://repo.anaconda.com/pkgs/main/linux-64/absl-py-0.1.10-py27_0.conda fetch
range {'Accept-Encoding': 'identity', 'Range': 'bytes=122880-128735'}, fetch
range {'Accept-Encoding': 'identity', 'Range': 'bytes=118496-122879'}, fetch
range {'Accept-Encoding': 'identity', 'Range': 'bytes=0-10239'}, fetch range
{'Accept-Encoding': 'identity', 'Range': 'bytes=10240-10269'}, fetch range
{'Accept-Encoding': 'identity', 'Range': 'bytes=10270-10303'}
```

Extracts entire info folder. Appears not to do the bytes-from-end
optimization.

Once you have the index, it would be possible to fetch everything else you want
in a single (compound?) Range request.


## Older format

bzip2 has a very large block size, and we don't know if the info/ directory
is finished early. However if we only want certain files from info/ we can stop
after we've seen them all. Fetching repodata and calling response.raw.tell()
after each tar member:

```
$ python -m metayaml.fetch_metadata \
    https://repo.anaconda.com/pkgs/main/linux-64/absl-py-0.1.10-py27_0.tar.bz2
128948 info/hash_input.json
128948 info/index.json
128948 info/files
128948 info/about.json
128948 info/paths.json
128948 info/LICENSE.txt
128948 info/git
128948 lib/python2.7/site-packages/absl_py-0.1.10-py2.7.egg-info/dependency_links.txt
128948 lib/python2.7/site-packages/absl_py-0.1.10-py2.7.egg-info/requires.txt
128948 lib/python2.7/site-packages/absl_py-0.1.10-py2.7.egg-info/top_level.txt
128948 lib/python2.7/site-packages/absl/__init__.pyc
128948 lib/python2.7/site-packages/absl/testing/__init__.pyc
128948 info/test/run_test.py
...
```

A larger package:
```
$ python -m metayaml.fetch_metadata \
    https://repo.anaconda.com/pkgs/main/linux-64/airflow-1.10.10-py36_0.tar.bz2
286720 info/hash_input.json
286720 info/has_prefix
286720 info/index.json
286720 info/about.json
286720 info/git
286720 info/files
286720 info/paths.json
286720 lib/python3.6/site-packages/airflow/alembic.ini
286720 lib/python3.6/site-packages/airflow/www/templates/airflow/variables/README.md
...
286720 info/test/test_time_dependencies.json
...
634880 lib/python3.6/site-packages/airflow/www/static/ace.js
634880 bin/airflow
```

```{toctree}
:maxdepth: 4

fetch_metadata
fetch_s3
lazy_wheel
package_streaming
transmute
```
