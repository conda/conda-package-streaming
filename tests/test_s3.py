# TODO support s3 as well
from pathlib import Path

import boto3
import pytest

from conda_package_streaming import fetch_s3


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


@pytest.fixture(scope="module")
def conda_paths(package_server):
    pkgs_dir = Path(package_server.app.pkgs_dir)
    conda_paths = []
    for path in pkgs_dir.iterdir():
        if path.name.endswith((".tar.bz2", ".conda")):
            conda_paths.append(path)
    return conda_paths


def test_head_objects(s3_client, conda_paths):
    bucket = "pkgs"  # independent of filesystem path
    for path in conda_paths:
        s3_client.head_object(Bucket=bucket, Key=path.name)


def test_stream_s3(s3_client, conda_paths):
    for path in conda_paths:
        members = fetch_s3.stream_meta(s3_client, "pkgs", path.name)
        print("stream s3", path.name)
        for tar, member in members:
            if member.name == "info/index.json":
                members.close()  # faster than waiting for gc?
                break
        else:
            pytest.fail("info/index.json not found")
