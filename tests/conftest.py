import socket

import pytest

DEAD_PROXY = "http://127.0.0.1:9"


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", help="run tests that use the internet")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs --network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    """Refuse sockets in this process, and point subprocesses' HTTP at a dead proxy.

    Tests marked network are exempt when --network is given.
    """
    if "network" in request.keywords and request.config.getoption("--network"):
        return

    def refuse(*args, **kwargs):
        raise OSError("network access in a test that is not marked network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.setenv(name, DEAD_PROXY)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
