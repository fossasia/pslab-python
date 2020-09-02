import pytest


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False)
    parser.addoption("--record", action="store_true", default=False)


@pytest.fixture
def integration(request):
    return request.config.getoption("--integration")


@pytest.fixture
def record(request):
    return request.config.getoption("--record")
