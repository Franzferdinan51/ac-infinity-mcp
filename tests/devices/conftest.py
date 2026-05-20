import pytest

from tests.fixtures.ai_plus_device_fixtures import AI_PLUS_DEVICE
from tests.fixtures.legacy_device_fixtures import LEGACY_11_DEVICE, LEGACY_18_DEVICE


@pytest.fixture
def legacy_11_device():
    return LEGACY_11_DEVICE.copy()


@pytest.fixture
def legacy_18_device():
    return LEGACY_18_DEVICE.copy()


@pytest.fixture
def ai_plus_device():
    return AI_PLUS_DEVICE.copy()
