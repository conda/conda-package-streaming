# TODO support s3 as well
from pathlib import Path

import boto3
import pytest


@pytest.fixture
def s3_client(package_server):
    host, port = package_server.server.server_address
    client = boto3.client(
        "s3",
        aws_access_key_id="test_id",
        aws_secret_access_key="test_key",
        endpoint_url=f"http://{host}:{port}",
        use_ssl=False,
        verify=False,
    )
    return client


def test_head_objects(package_server, s3_client):
    pkgs_dir = Path(package_server.app.pkgs_dir)
    bucket = "pkgs"  # independent of filesystem path
    for path in pkgs_dir.iterdir():
        if path.name.endswith((".tar.bz2", ".conda")):
            print(s3_client.head_object(Bucket=bucket, Key=path.name))


# response body shows a lot, implements read but not seek
#
# 'close',
# 'closed',
# 'fileno',
# 'flush',
# 'isatty',
# 'iter_chunks',
# 'iter_lines',
# 'next',
# 'read',
# 'readable',
# 'readline',
# 'readlines',
# 'seek',
# 'seekable',
# 'set_socket_timeout',
# 'tell',
# 'truncate',
# 'writable',
# 'writelines'

# boto3 range request:
# body = obj.get(Range='bytes=32-64')['Body']
