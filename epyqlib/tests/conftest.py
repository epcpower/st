import pytest


def pytest_addoption(parser):
    parser.addoption(
        '--device-present',
        action='store_true',
        default=False,
        help='Run tests that require a device be connected'
    )
    parser.addoption(
        '--run-factory',
        action='store_true',
        default=False,
        help='Run tests that require a factory device file'
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--device-present"):
        device_present = pytest.mark.skip(
            reason="need --device-present option to run",
        )
        for item in items:
            if "require_device" in item.keywords:
                item.add_marker(device_present)

    if not config.getoption("--run-factory"):
        factory = pytest.mark.skip(
            reason="need --run-factory option to run",
        )
        for item in items:
            if "factory" in item.keywords:
                item.add_marker(factory)
