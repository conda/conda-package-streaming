# conda_package_streaming

Fetch metadata from remote .conda or .tar.bz2 package.

Try to fetch less than the whole file if possible.

Zip (.conda) is made for this:

```
$ python -m conda_package_streaming.url https://repo.anaconda.com/pkgs/main/osx-64/sqlalchemy-1.4.32-py310hca72f7f_0.conda /tmp/
DEBUG:conda_package_streaming.lazy_wheel:bytes=-10240
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): repo.anaconda.com:443
DEBUG:urllib3.connectionpool:https://repo.anaconda.com:443 "GET /pkgs/main/osx-64/sqlalchemy-1.4.32-py310hca72f7f_0.conda HTTP/1.1" 206 10240
DEBUG:conda_package_streaming.lazy_wheel:bytes=43-38176
DEBUG:urllib3.connectionpool:https://repo.anaconda.com:443 "GET /pkgs/main/osx-64/sqlalchemy-1.4.32-py310hca72f7f_0.conda HTTP/1.1" 206 38134
DEBUG:conda_package_streaming.lazy_wheel:prefetch 43-38177

$ curl -s -I https://repo.anaconda.com/pkgs/main/osx-64/sqlalchemy-1.4.32-py310hca72f7f_0.conda | grep content-length
content-length: 1984926
```

We fetch 10240 + 38134 = 48374 bytes in two requests of this 1984926-byte
package.


## Older format

bzip2 has a very large block size, and we don't know if the info/ directory is
finished before reading the entire archive. However if we only want certain
files from info/ we can stop after we've seen them all. Fetching repodata and
calling response.raw.tell() after each tar member:

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
# Fetch https://repo.anaconda.com/pkgs/main/linux-64/airflow-1.10.10-py36_0.tar.bz2
# Printing bytes transferred after each archive member,
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

url
s3
lazy_wheel
package_streaming
extract
transmute
create
```
