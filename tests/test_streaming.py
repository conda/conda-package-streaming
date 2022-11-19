import json

import pytest

from conda_package_streaming import package_streaming


def test_package_streaming(conda_paths):
    for path in conda_paths:
        if str(path).endswith(".conda"):
            with pytest.raises(LookupError):
                package_streaming.stream_conda_component(path, component="notfound")

        with pytest.raises(ValueError):
            package_streaming.stream_conda_component("notapackage.rar")


def test_early_exit(conda_paths):
    for package in conda_paths:
        print(package)
        stream = iter(package_streaming.stream_conda_info(package))
        found = False
        for tar, member in stream:
            assert not found, "early exit did not work"
            if member.name == "info/index.json":
                reader = tar.extractfile(member)
                if reader:
                    json.load(reader)
                    found = True
                stream.close()  # PEP 342 close()
        # stream_conda_info doesn't close a passed-in fileobj, but a
        # filename should be closed.
        assert found, f"index.json not found in {package}"
