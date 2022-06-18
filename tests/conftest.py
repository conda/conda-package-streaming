import pytest
import server


@pytest.fixture(scope="session")
def package_server():
    thread = server.get_server_thread()
    thread.start()
    return thread
