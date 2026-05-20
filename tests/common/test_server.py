"""Unit tests for server.py async tools and helper functions."""

import json
from unittest.mock import patch

import pytest

from ac_infinity_mcp.server import (
    _filter_readings_by_time,
    _parse_duration_seconds,
    apply_sampling,
    average_readings,
    check_vpd_drift,
    discover_devices,
    get_all_device_readings,
    get_device_reading,
    get_historical_readings,
    mcp_server,
)
from tests.conftest import MOCK_DEVICE_LEGACY


def _make_history_record(ts: str, temp_c: float = 24.0, humidity: float = 55.0,
                         vpd: float = 1.5, ports=None) -> dict:
    return {
        "timestamp": ts,
        "temperature_c": temp_c,
        "temperature_f": round(temp_c * 9 / 5 + 32, 1),
        "humidity": humidity,
        "vpd": vpd,
        "ports": ports or [],
    }


# ============ Smoke / symbol checks ============

def test_mcp_server_name():
    assert mcp_server.name == "ac-infinity-mcp"


# ============ discover_devices ============

async def test_discover_devices_success(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await discover_devices()
    data = json.loads(result)
    assert "devices" in data
    assert len(data["devices"]) == 1
    assert data["devices"][0]["device_id"] == "C58ZA"


async def test_discover_devices_empty(mock_client):
    mock_client.get_devices.return_value = []
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await discover_devices()
    data = json.loads(result)
    assert data["devices"] == []


async def test_discover_devices_none(mock_client):
    mock_client.get_devices.return_value = None
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await discover_devices()
    data = json.loads(result)
    assert data["devices"] == []


async def test_discover_devices_online_offline_status(mock_client):
    mock_client.get_devices.return_value = [
        {"devCode": "A1", "devName": "Device A", "online": True},
        {"devCode": "B2", "devName": "Device B", "online": False},
    ]
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await discover_devices()
    data = json.loads(result)
    by_id = {d["device_id"]: d for d in data["devices"]}
    assert by_id["A1"]["status"] == "online"
    assert by_id["B2"]["status"] == "offline"


async def test_discover_devices_client_not_initialized():
    with patch("ac_infinity_mcp.server.aci_client", None):
        result = await discover_devices()
    data = json.loads(result)
    assert "error" in data


# ============ get_device_reading ============

async def test_get_device_reading_success(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_device_reading("C58ZA")
    data = json.loads(result)
    assert data["device_id"] == "C58ZA"
    assert "temperature_c" in data
    assert "humidity" in data
    assert "vpd" in data


async def test_get_device_reading_device_not_found(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_device_reading("NOTEXIST")
    data = json.loads(result)
    assert "error" in data
    assert "NOTEXIST" in data["error"]


async def test_get_device_reading_no_devices(mock_client):
    mock_client.get_devices.return_value = None
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_device_reading("C58ZA")
    data = json.loads(result)
    assert "error" in data


# ============ get_all_device_readings ============

async def test_get_all_device_readings_success(mock_client):
    second = {**MOCK_DEVICE_LEGACY, "devCode": "D2"}
    mock_client.get_devices.return_value = [MOCK_DEVICE_LEGACY, second]
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_all_device_readings()
    data = json.loads(result)
    assert "readings" in data
    assert len(data["readings"]) == 2


async def test_get_all_device_readings_no_devices(mock_client):
    mock_client.get_devices.return_value = None
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_all_device_readings()
    data = json.loads(result)
    assert "error" in data


async def test_get_all_device_readings_parse_error_isolated(mock_client):
    good_device = MOCK_DEVICE_LEGACY
    bad_device = {**MOCK_DEVICE_LEGACY, "devCode": "BAD"}
    mock_client.get_devices.return_value = [good_device, bad_device]

    def side_effect(device):
        if device.get("devCode") == "BAD":
            raise ValueError("simulated parse failure")
        return mock_client.parse_device_data.return_value

    mock_client.parse_device_data.side_effect = side_effect
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_all_device_readings()
    data = json.loads(result)
    readings = {r["device_id"]: r for r in data["readings"]}
    assert "error" in readings["BAD"]
    assert "error" not in readings["C58ZA"]


# ============ get_historical_readings ============

async def test_get_historical_readings_success(mock_client):
    base_ts = 1714000000
    raw_records = [
        {
            "createTime": base_ts + i * 3600,
            "temperature": 2400,
            "fTemperature": 7520,
            "humidity": 5500,
            "vpdNums": 150,
            "portSpead": 0,
            "portStatus": 0,
            "devPortCount": 2,
        }
        for i in range(5)
    ]
    mock_client.get_historical_data.return_value = raw_records
    mock_client.parse_history_record.side_effect = lambda r, port_names=None: {
        "timestamp": f"2024-04-25T{(r['createTime'] - base_ts) // 3600:02d}:00:00Z",
        "temperature_c": 24.0,
        "temperature_f": 75.2,
        "humidity": 55.0,
        "vpd": 1.5,
        "ports": [],
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "2024-04-25", "2024-04-25", "raw")
    data = json.loads(result)
    assert "readings" in data
    assert len(data["readings"]) == 5
    assert "statistics" in data


async def test_get_historical_readings_invalid_date_format(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "not-a-date", "2024-04-25")
    data = json.loads(result)
    assert "error" in data
    assert "YYYY-MM-DD" in data["error"]


async def test_get_historical_readings_start_after_end(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "2024-04-26", "2024-04-25")
    data = json.loads(result)
    assert "error" in data
    assert "start_date" in data["error"]


async def test_get_historical_readings_invalid_interval(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "2024-04-25", "2024-04-25", "2x")
    data = json.loads(result)
    assert "error" in data
    assert "sample_interval" in data["error"].lower() or "2x" in data["error"]


async def test_get_historical_readings_no_device(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("NOTEXIST", "2024-04-25", "2024-04-25")
    data = json.loads(result)
    assert "error" in data


async def test_get_historical_readings_no_records(mock_client):
    mock_client.get_historical_data.return_value = []
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "2024-04-25", "2024-04-25")
    data = json.loads(result)
    assert "error" in data
    assert "No readings" in data["error"]


async def test_get_historical_readings_sampling_1h(mock_client):
    base_ts = 1714000000
    # 3 records within the same 1h bucket
    raw_records = [
        {
            "createTime": base_ts + i * 600,
            "temperature": 2400, "fTemperature": 7520,
            "humidity": 5500, "vpdNums": 150,
            "portSpead": 0, "portStatus": 0, "devPortCount": 2,
        }
        for i in range(3)
    ]
    mock_client.get_historical_data.return_value = raw_records
    mock_client.parse_history_record.side_effect = lambda r, port_names=None: {
        "timestamp": f"2024-04-25T00:{(r['createTime'] - base_ts) // 60:02d}:00Z",
        "temperature_c": 24.0,
        "temperature_f": 75.2,
        "humidity": 55.0,
        "vpd": 1.5,
        "ports": [],
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "2024-04-25", "2024-04-25", "1h")
    data = json.loads(result)
    assert len(data["readings"]) == 1


async def test_get_historical_readings_statistics_computed(mock_client):
    base_ts = 1714000000
    raw_records = [
        {"createTime": base_ts + i * 3600, "temperature": 2400, "fTemperature": 7520,
         "humidity": 5500, "vpdNums": 150, "portSpead": 0, "portStatus": 0, "devPortCount": 2}
        for i in range(3)
    ]
    mock_client.get_historical_data.return_value = raw_records
    mock_client.parse_history_record.side_effect = lambda r, port_names=None: {
        "timestamp": f"2024-04-25T{(r['createTime'] - base_ts) // 3600:02d}:00:00Z",
        "temperature_c": 24.0, "temperature_f": 75.2,
        "humidity": 55.0, "vpd": 1.5, "ports": [],
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await get_historical_readings("C58ZA", "2024-04-25", "2024-04-25", "raw")
    data = json.loads(result)
    stats = data["statistics"]
    assert "temperature_c" in stats
    assert stats["temperature_c"]["avg"] == 24.0
    assert "vpd" in stats


# ============ check_vpd_drift ============

async def test_check_vpd_drift_ok(mock_client):
    mock_client.parse_device_data.return_value = {
        **mock_client.parse_device_data.return_value,
        "vpd": 1.24,
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await check_vpd_drift("C58ZA", "veg")
    data = json.loads(result)
    assert data["status"] == "OK"
    assert data["alert"] is None


async def test_check_vpd_drift_low(mock_client):
    mock_client.parse_device_data.return_value = {
        **mock_client.parse_device_data.return_value,
        "vpd": 0.5,
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await check_vpd_drift("C58ZA", "veg")
    data = json.loads(result)
    assert data["status"] == "LOW"
    assert "below target" in data["alert"]


async def test_check_vpd_drift_high(mock_client):
    mock_client.parse_device_data.return_value = {
        **mock_client.parse_device_data.return_value,
        "vpd": 2.5,
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await check_vpd_drift("C58ZA", "veg")
    data = json.loads(result)
    assert data["status"] == "HIGH"
    assert "exceeds target" in data["alert"]


async def test_check_vpd_drift_unknown_stage_defaults_to_veg(mock_client):
    mock_client.parse_device_data.return_value = {
        **mock_client.parse_device_data.return_value,
        "vpd": 1.24,
    }
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await check_vpd_drift("C58ZA", "nonexistent_stage")
    data = json.loads(result)
    assert "status" in data


async def test_check_vpd_drift_device_not_found(mock_client):
    with patch("ac_infinity_mcp.server.aci_client", mock_client):
        result = await check_vpd_drift("NOTEXIST", "veg")
    data = json.loads(result)
    assert "error" in data


# ============ _parse_duration_seconds ============

@pytest.mark.parametrize("interval,expected", [
    ("1m", 60),
    ("5m", 300),
    ("15m", 900),
    ("30m", 1800),
    ("1h", 3600),
    ("2h", 7200),
    ("6h", 21600),
    ("12h", 43200),
    ("1d", 86400),
    ("daily", 86400),
])
def test_parse_duration_seconds_valid_values(interval, expected):
    assert _parse_duration_seconds(interval) == expected


@pytest.mark.parametrize("interval", ["2x", "abc", "", "1y", "h1"])
def test_parse_duration_seconds_invalid_raises(interval):
    with pytest.raises(ValueError):
        _parse_duration_seconds(interval)


# ============ _filter_readings_by_time ============

_READINGS = [
    _make_history_record("2024-04-25T08:00:00Z"),
    _make_history_record("2024-04-25T12:00:00Z"),
    _make_history_record("2024-04-25T16:00:00Z"),
    _make_history_record("2024-04-25T20:00:00Z"),
]


def test_filter_readings_by_time_no_filter():
    result = _filter_readings_by_time(_READINGS)
    assert len(result) == 4


def test_filter_readings_by_time_start_only():
    result = _filter_readings_by_time(_READINGS, time_start="12:00")
    assert len(result) == 3
    assert result[0]["timestamp"] == "2024-04-25T12:00:00Z"


def test_filter_readings_by_time_end_only():
    result = _filter_readings_by_time(_READINGS, time_end="16:00")
    assert len(result) == 3
    assert result[-1]["timestamp"] == "2024-04-25T16:00:00Z"


def test_filter_readings_by_time_both():
    result = _filter_readings_by_time(_READINGS, time_start="12:00", time_end="16:00")
    assert len(result) == 2


def test_filter_readings_bad_timestamp_skipped():
    readings = [
        _make_history_record("2024-04-25T12:00:00Z"),
        {"timestamp": "NOT_A_TIMESTAMP", "temperature_c": 24.0},
    ]
    result = _filter_readings_by_time(readings, time_start="10:00")
    assert len(result) == 1


# ============ apply_sampling ============

def test_apply_sampling_raw_passthrough():
    readings = [{"timestamp": "2026-01-01T00:00:00Z", "temperature_c": 24.0}]
    assert apply_sampling(readings, "raw") == readings


def test_apply_sampling_1h_averaging():
    readings = [
        _make_history_record("2024-04-25T10:00:00Z", temp_c=24.0),
        _make_history_record("2024-04-25T10:30:00Z", temp_c=26.0),
        _make_history_record("2024-04-25T10:45:00Z", temp_c=25.0),
        _make_history_record("2024-04-25T11:00:00Z", temp_c=24.0),
    ]
    result = apply_sampling(readings, "1h")
    assert len(result) == 2


def test_apply_sampling_daily_alias():
    readings = [_make_history_record("2024-04-25T12:00:00Z")]
    r1 = apply_sampling(readings, "daily")
    r2 = apply_sampling(readings, "1d")
    assert len(r1) == len(r2)


# ============ average_readings ============

def test_average_readings_empty():
    assert average_readings([]) == {}


def test_average_readings_single():
    reading = _make_history_record("2024-04-25T10:00:00Z", temp_c=24.0, humidity=55.0, vpd=1.5)
    result = average_readings([reading])
    assert result["temperature_c"] == 24.0
    assert result["humidity"] == 55.0
    assert result["vpd"] == 1.5


def test_average_readings_multiple():
    readings = [
        _make_history_record("2024-04-25T10:00:00Z", temp_c=20.0),
        _make_history_record("2024-04-25T10:30:00Z", temp_c=30.0),
    ]
    result = average_readings(readings)
    assert result["temperature_c"] == 25.0


def test_average_readings_with_ports():
    readings = [
        {
            "timestamp": "2024-04-25T10:00:00Z",
            "temperature_c": 24.0, "temperature_f": 75.2,
            "humidity": 55.0, "vpd": 1.5,
            "ports": [{"port": 1, "name": "Fan", "speed": 4, "on": True}],
        },
        {
            "timestamp": "2024-04-25T10:30:00Z",
            "temperature_c": 24.0, "temperature_f": 75.2,
            "humidity": 55.0, "vpd": 1.5,
            "ports": [{"port": 1, "name": "Fan", "speed": 6, "on": True}],
        },
    ]
    result = average_readings(readings)
    assert len(result["ports"]) == 1
    assert result["ports"][0]["speed"] == 5.0
