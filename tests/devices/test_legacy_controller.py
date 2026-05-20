"""Tests for legacy controller behavior (devType 11 and 18)."""

import pytest

from ac_infinity_mcp.controller import ControllerType, build_write_payload, detect_controller_type

# ============ detect_controller_type ============

def test_detect_controller_type_devtype_11():
    assert detect_controller_type({"devType": 11}) == ControllerType.LEGACY


def test_detect_controller_type_devtype_18():
    assert detect_controller_type({"devType": 18}) == ControllerType.LEGACY


def test_detect_controller_type_defaults_to_legacy():
    assert detect_controller_type({}) == ControllerType.LEGACY


def test_detect_controller_type_new_framework_flag_overrides_legacy_devtype():
    # newFrameworkDevice=True takes precedence even when devType says legacy
    result = detect_controller_type({"devType": 11, "newFrameworkDevice": True})
    assert result == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_legacy_11_fixture(legacy_11_device):
    assert detect_controller_type(legacy_11_device) == ControllerType.LEGACY


def test_detect_controller_type_legacy_18_fixture(legacy_18_device):
    assert detect_controller_type(legacy_18_device) == ControllerType.LEGACY


# ============ build_write_payload — Phase 8 stubs ============
# These tests currently verify the Phase 8 stub raises NotImplementedError.
# When Phase 8 implements build_write_payload, remove the pytest.raises block
# and activate the assertion noted in each docstring.

def test_build_write_payload_raises_not_implemented_legacy():
    """Phase 8 must implement read-merge-write path for LEGACY controllers.

    Requirements: all 77 API fields required; modeSetid must be excluded;
    modeType=2 coercion when onSpead > 0.
    """
    with pytest.raises(NotImplementedError):
        build_write_payload({}, {}, ControllerType.LEGACY)


def test_build_write_payload_will_exclude_modeSetid_legacy():
    """modeSetid must NEVER appear in the legacy write payload — causes 403 error.

    Phase 8: convert to assertion:
        result = build_write_payload(current_settings, {}, ControllerType.LEGACY)
        assert "modeSetid" not in result
    """
    # TODO: Phase 8 — convert to assertion
    with pytest.raises(NotImplementedError):
        build_write_payload({}, {}, ControllerType.LEGACY)


def test_build_write_payload_will_coerce_modeType_when_speed_nonzero():
    """When onSpead > 0, modeType must be set to 2 or the change doesn't persist.

    Phase 8: convert to assertion:
        result = build_write_payload({}, {"onSpead": 5}, ControllerType.LEGACY)
        assert result["modeType"] == 2
    """
    # TODO: Phase 8 — convert to assertion
    with pytest.raises(NotImplementedError):
        build_write_payload({}, {"onSpead": 5}, ControllerType.LEGACY)
