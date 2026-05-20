"""Tests for AI+ controller behavior (devType 20+, newFrameworkDevice=True)."""

import pytest

from ac_infinity_mcp.controller import ControllerType, build_write_payload, detect_controller_type

# ============ detect_controller_type ============

def test_detect_controller_type_devtype_20():
    assert detect_controller_type({"devType": 20}) == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_new_framework_flag():
    assert detect_controller_type({"newFrameworkDevice": True}) == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_devtype_25():
    # Future higher-end controller — any devType >= 20 is new framework
    assert detect_controller_type({"devType": 25}) == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_ai_plus_fixture(ai_plus_device):
    assert detect_controller_type(ai_plus_device) == ControllerType.NEW_FRAMEWORK


# ============ build_write_payload — Phase 8 stub ============
# This test currently verifies the Phase 8 stub raises NotImplementedError.
# When Phase 8 implements build_write_payload, remove the pytest.raises block
# and activate the assertion noted in the docstring.

def test_build_write_payload_raises_not_implemented_new_framework():
    """Phase 8 must implement the static full-payload pattern for AI+ controllers.

    Requirements: start from static 77-field defaults dict, overlay target fields,
    no pre-fetch required. Uses PUT /api/dev/modeAndSetting endpoint (not addDevMode).

    Phase 8: convert to assertion:
        result = build_write_payload({}, {"onSpead": 5}, ControllerType.NEW_FRAMEWORK)
        assert len(result) >= 77
        assert "modeSetid" not in result
    """
    # TODO: Phase 8 — convert to assertion
    with pytest.raises(NotImplementedError):
        build_write_payload({}, {}, ControllerType.NEW_FRAMEWORK)
