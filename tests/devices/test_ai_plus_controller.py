"""Tests for AI+ controller behavior (devType 20+, newFrameworkDevice=True)."""

from ac_infinity_mcp.controller import ControllerType, build_write_payload, detect_controller_type
from tests.fixtures.mock_mode_settings_ai_plus import (
    MOCK_MODE_SETTINGS_AI_PLUS_PORT1,
    MOCK_MODE_SETTINGS_AI_PLUS_PORT1_FLAT,
)

# ============ detect_controller_type ============

def test_detect_controller_type_devtype_20():
    assert detect_controller_type({"devType": 20}) == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_new_framework_flag():
    assert detect_controller_type({"newFrameworkDevice": True}) == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_devtype_25():
    assert detect_controller_type({"devType": 25}) == ControllerType.NEW_FRAMEWORK


def test_detect_controller_type_ai_plus_fixture(ai_plus_device):
    assert detect_controller_type(ai_plus_device) == ControllerType.NEW_FRAMEWORK


# ============ build_write_payload — AI+ path ============

def test_build_write_payload_ai_plus_merges_updates():
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {"onSpead": 5}, ControllerType.NEW_FRAMEWORK
    )
    assert result["onSpead"] == 5


def test_build_write_payload_ai_plus_strips_modeSetid():
    """Quirk 11: strip modeSetid for AI+ as well — same behavior as legacy."""
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {}, ControllerType.NEW_FRAMEWORK
    )
    assert "modeSetid" not in result


def test_build_write_payload_ai_plus_modeType_2_when_speed_nonzero():
    """Quirk 12 applies to AI+ as well."""
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {"onSpead": 7}, ControllerType.NEW_FRAMEWORK
    )
    assert result["modeType"] == 2


def test_build_write_payload_ai_plus_excludes_devSetting():
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {}, ControllerType.NEW_FRAMEWORK
    )
    assert "devSetting" not in result


def test_build_write_payload_ai_plus_excludes_fieldSet():
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {}, ControllerType.NEW_FRAMEWORK
    )
    assert "fieldSet" not in result


def test_build_write_payload_ai_plus_flat_field_count():
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {}, ControllerType.NEW_FRAMEWORK
    )
    assert len(result) == len(MOCK_MODE_SETTINGS_AI_PLUS_PORT1_FLAT) - 1  # minus modeSetid


def test_build_write_payload_ai_plus_preserves_surplus_null():
    """AI+ has surplus=None (not 0 like legacy) — verify it passes through."""
    result = build_write_payload(
        MOCK_MODE_SETTINGS_AI_PLUS_PORT1, {}, ControllerType.NEW_FRAMEWORK
    )
    assert result["surplus"] is None
