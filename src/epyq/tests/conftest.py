import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-manual",
        action="store_true",
        default=False,
        help="Run tests that require a device be connected",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-manual"):
        manual = pytest.mark.skip(
            reason="need --run-manual option to run",
        )
        for item in items:
            if "manual" in item.keywords:
                item.add_marker(manual)
