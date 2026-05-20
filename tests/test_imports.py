"""Smoke tests: verify all modules import cleanly and expose expected symbols."""

from ac_infinity_mcp import __version__
from ac_infinity_mcp.analytics import ActivityReport, HealthScore, TrendReport
from ac_infinity_mcp.controller import ControllerType, detect_controller_type
from ac_infinity_mcp.schema import (
    ACInfinityAuthError,
    ACInfinityConfigError,
    ACInfinityDeviceError,
    ACInfinityError,
    ACIReading,
    VPDTargets,
    calculate_vpd,
)
from ac_infinity_mcp.server import apply_sampling, average_readings, mcp_server


def test_version():
    assert __version__ == "0.1.0"


def test_schema_exception_hierarchy():
    assert issubclass(ACInfinityAuthError, ACInfinityError)
    assert issubclass(ACInfinityDeviceError, ACInfinityError)
    assert issubclass(ACInfinityConfigError, ACInfinityError)


def test_vpd_targets_defaults():
    t = VPDTargets()
    assert t.veg == (1.0, 1.5)
    assert t.seedling == (0.8, 1.2)
    assert t.late_flower == (1.2, 1.8)


def test_calculate_vpd_range():
    vpd = calculate_vpd(25.0, 60.0)
    assert 0.5 < vpd < 2.0


def test_acireading_to_dict():
    r = ACIReading(
        timestamp="2026-01-01T00:00:00Z",
        device_id="C58ZA",
        device_name="Test",
        temperature_c=24.0,
        temperature_f=75.2,
        humidity=60.0,
        vpd=1.24,
    )
    d = r.to_dict()
    assert d["device_id"] == "C58ZA"
    assert d["vpd"] == 1.24


def test_mcp_server_name():
    assert mcp_server.name == "ac-infinity-mcp"


def test_apply_sampling_raw_passthrough():
    readings = [{"timestamp": "2026-01-01T00:00:00Z", "temperature_c": 24.0}]
    assert apply_sampling(readings, "raw") == readings


def test_average_readings_empty():
    assert average_readings([]) == {}


def test_controller_type_legacy_devtype_11():
    assert detect_controller_type({"devType": 11}) == ControllerType.LEGACY


def test_controller_type_legacy_devtype_18():
    assert detect_controller_type({"devType": 18}) == ControllerType.LEGACY


def test_controller_type_new_framework_devtype_20():
    assert detect_controller_type({"devType": 20}) == ControllerType.NEW_FRAMEWORK


def test_controller_type_new_framework_flag():
    result = detect_controller_type({"devType": 11, "newFrameworkDevice": True})
    assert result == ControllerType.NEW_FRAMEWORK


def test_controller_type_defaults_to_legacy():
    assert detect_controller_type({}) == ControllerType.LEGACY


def test_analytics_dataclasses_are_importable():
    # Verify dataclass fields are defined correctly
    assert hasattr(HealthScore, "__dataclass_fields__")
    assert hasattr(TrendReport, "__dataclass_fields__")
    assert hasattr(ActivityReport, "__dataclass_fields__")
    assert "score" in HealthScore.__dataclass_fields__
    assert "slope" in TrendReport.__dataclass_fields__
    assert "uptime_pct" in ActivityReport.__dataclass_fields__
