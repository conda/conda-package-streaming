from contextlib import closing
from pathlib import Path

import pytest
import requests

from conda_package_streaming import fetch_metadata, package_streaming


@pytest.fixture
def package_url(package_server):
    """
    Base url for all test packages.
    """
    host, port = package_server.server.server_address
    return f"http://{host}:{port}/pkgs"


@pytest.fixture
def package_urls(package_server, package_url):
    pkgs_dir = Path(package_server.app.pkgs_dir)
    urls = []
    for path in pkgs_dir.iterdir():
        if path.name.endswith((".tar.bz2", ".conda")):
            urls.append(f"{package_url}/{path.name}")
    return urls


def test_stream_url(package_urls):
    for url in package_urls:
        with closing(fetch_metadata.stream_meta(url)) as members:
            print("stream_url", url)
            for tar, member in members:
                if member.name == "info/index.json":
                    break
            else:
                pytest.fail("info/index.json not found")
