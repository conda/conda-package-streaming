import io
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path
from zipfile import ZipFile

import pytest
from requests import HTTPError, Session

from conda_package_streaming import lazy_wheel
from conda_package_streaming.lazy_wheel import LazyConda
from conda_package_streaming.url import (
    conda_reader_for_url,
    extract_conda_info,
    stream_conda_info,
)

LIMIT = 16


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
    conda = []
    tar_bz2 = []

    for path in pkgs_dir.iterdir():
        if len(conda) > LIMIT and len(tar_bz2) > LIMIT:
            break
        url = f"{package_url}/{path.name}"
        if path.name.endswith(".tar.bz2") and len(tar_bz2) < LIMIT:
            tar_bz2.append(url)
        elif path.name.endswith(".conda") and len(conda) < LIMIT:
            conda.append(url)
    # interleave
    urls = []
    for pair in zip(conda, tar_bz2):
        urls.extend(pair)
    return urls


def test_stream_url(package_urls):
    with pytest.raises(ValueError):
        next(stream_conda_info("https://localhost/notaconda.rar"))

    for url in package_urls:
        with closing(stream_conda_info(url)) as members:
            print("stream_url", url)
            for tar, member in members:
                if member.name == "info/index.json":
                    break
            else:
                pytest.fail("info/index.json not found")


def test_fetch_meta(package_urls):
    for url in package_urls:
        with tempfile.TemporaryDirectory() as destdir:
            extract_conda_info(url, destdir)


def test_lazy_wheel(package_urls):
    lazy_tests = 7
    for url in package_urls:
        if url.endswith(".conda"):
            # API works with `.tar.bz2` but only returns LazyConda for `.conda`
            filename, conda = conda_reader_for_url(url)
            assert filename == url.rsplit("/")[-1]
            with conda:
                assert isinstance(conda, LazyConda)
                assert conda.mode == "rb"
                assert conda.readable()
                assert not conda.writable()
                assert not conda.closed

                request_count = conda._request_count

                # did we really prefetch the info?
                zf = ZipFile(conda)  # type: ignore
                filename = filename[: -len(".conda")]
                zf.open(f"info-{filename}.tar.zst").read()

                assert (
                    conda._request_count == request_count
                ), "info required extra GET request"
                assert conda._request_count <= 3

                conda.prefetch("not-appearing-in-archive.txt")

                # zip will figure this out naturally; delete method?
                conda._check_zip()

            lazy_tests -= 1
            if lazy_tests <= 0:
                break
    else:
        raise LookupError(
            "not enough .conda packages found %d %s" % (lazy_tests, package_urls)
        )

    with pytest.raises(HTTPError):
        conda_reader_for_url(package_urls[0] + ".404.conda")

    class Session200(Session):
        def get(self, *args, **kwargs):
            response = super().get(*args, **kwargs)
            response.status_code = 200
            return response

    with pytest.raises(lazy_wheel.HTTPRangeRequestUnsupported):
        LazyConda(package_urls[0], Session200())

    for url in package_urls:
        if url.endswith(".tar.bz2"):
            LazyConda(url, Session())._check_zip()
            break
    else:
        raise LookupError("no .tar.bz2 packages found")


def test_no_file_after_info():
    """
    If info is the last file, LazyConda must fetch (start of info file .. start
    of zip directory) instead of to the next file in the zip.
    """

    class MockBytesIO(io.BytesIO):
        prefetch = LazyConda.prefetch

        @contextmanager
        def _stay(self):
            yield

    zip = MockBytesIO()
    zf = ZipFile(zip, "w")
    zf.writestr("info-test.tar.zst", b"00000000")  # a short file
    zf.close()

    zip.prefetch("test")


@pytest.mark.skip()
def test_obsolete_lazy_wheel_selftest():
    import logging

    import requests

    logging.basicConfig(level=logging.DEBUG)

    session = requests.Session()

    lzoh = lazy_wheel.LazyZipOverHTTP(
        "https://repodata.fly.dev/repo.anaconda.com/pkgs/main/win-32/current_repodata.jlap",
        session,
    )

    lzoh.seek(1024)
    lzoh.read(768)
    lzoh.seek(0)

    # compare against regular fetch
    with open("outfile.txt", "wb+") as out:
        buf = b" "
        while buf:
            buf = lzoh.read(1024 * 10)
            print(list(zip(lzoh._left, lzoh._right)), lzoh._length)
            if not buf:
                break
            out.write(buf)
