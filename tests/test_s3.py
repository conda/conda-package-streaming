import boto3
import pytest

from conda_package_streaming import s3

LIMIT = 16


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


def test_head_objects(s3_client, conda_paths):
    bucket = "pkgs"  # independent of filesystem path
    for path in conda_paths[:LIMIT]:
        s3_client.head_object(Bucket=bucket, Key=path.name)


def test_stream_s3(s3_client, conda_paths):
    with pytest.raises(ValueError):
        next(s3.stream_conda_info(s3_client, "pkgs", "notaconda.rar"))

    for path in conda_paths[:LIMIT]:
        members = s3.stream_conda_info(s3_client, "pkgs", path.name)
        print("stream s3", path.name)
        for tar, member in members:
            if member.name == "info/index.json":
                members.close()  # faster than waiting for gc?
                break
        else:
            pytest.fail("info/index.json not found")
