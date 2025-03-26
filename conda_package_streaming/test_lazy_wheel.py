import re

import requests
import responses
from requests.models import PreparedRequest
from responses import matchers

from conda_package_streaming.lazy_wheel import LazyZipOverHTTP

HTTP_FULL_RANGE_PATTERN = re.compile(r"bytes=(\d+)-(\d+)$")
HTTP_END_RANGE_PATTERN = re.compile(r"bytes=-(\d+)$")


class TestLazyZipOverHTTP:
    @staticmethod
    def generate_zero_bytes(length_bytes: int) -> bytes:
        return bytes(length_bytes)

    @staticmethod
    def successful_http_stream_callback_wrapper(file: bytes):
        # https://datatracker.ietf.org/doc/html/rfc7233
        def _callback(request: PreparedRequest):
            full_pattern_match = HTTP_FULL_RANGE_PATTERN.match(request.headers["Range"])
            end_pattern_match = HTTP_END_RANGE_PATTERN.match(request.headers["Range"])

            if full_pattern_match:
                start_range = int(full_pattern_match.group(1))
                end_range = int(full_pattern_match.group(2))

                assert start_range >= 0
                assert end_range >= 0
                assert start_range < end_range

                if start_range >= len(file):
                    # Range Not Satisfiable
                    return 416, {}, b""

                # truncate to file length
                end_range = min(end_range, len(file) - 1)
                content_length = end_range - start_range + 1  # the bounds are inclusive
            else:
                assert end_pattern_match

                content_length_requested = int(end_pattern_match.group(1))
                assert content_length_requested >= 0
                content_length = min(content_length_requested, len(file))

                start_range = len(file) - content_length
                end_range = len(file) - 1

            headers = {
                "Content-Length": str(content_length),
                "Content-Range": f"bytes {start_range}-{end_range}/{len(file)}",
            }

            # this is not inlined because black and flake8 disagree on how to format it
            end_file_range = end_range + 1

            return 206, headers, file[start_range:end_file_range]

        return _callback

    @responses.activate
    def test_init_stream_successful(self):
        responses.add_callback(
            responses.GET,
            "https://example.com/test.zip",
            callback=self.successful_http_stream_callback_wrapper(
                self.generate_zero_bytes(10000)
            ),
            content_type="application/zip",
        )

        session = requests.Session()
        lazy_zip = LazyZipOverHTTP("https://example.com/test.zip", session)
        lazy_zip.read()

    @responses.activate
    def test_init_stream_retry_without_range(self):
        """
        Some package servers (Artifactory) incorrectly respond with 416 (Range Not Satisfiable)
        when the file is smaller than the range requested.
        This violates RFC 7233, but we cope with it by retrying without Range, requesting the full
        file.
        """
        responses.add(
            responses.GET,
            url="https://example.com/test.zip",
            status=416,
            match=[matchers.header_matcher({"Range": re.compile(r".*")})],
        )

        responses.add(
            responses.GET,
            url="https://example.com/test.zip",
            body=self.generate_zero_bytes(10000),
            content_type="application/zip",
        )

        session = requests.Session()
        lazy_zip = LazyZipOverHTTP("https://example.com/test.zip", session)
        lazy_zip.read()
