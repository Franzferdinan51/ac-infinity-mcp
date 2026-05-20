"""Unit tests for ACInfinityClient data-parsing methods (no HTTP calls)."""

import pytest

from ac_infinity_mcp.client import ACInfinityClient


@pytest.fixture
def client():
    return ACInfinityClient("test@example.com", "password")


# ---- parse_device_data ----

MOCK_DEVICE = {
    "devCode": "C58ZA",
    "devName": "Test Controller",
    "deviceInfo": {
        "temperature": 2350,    # 23.50°C
        "temperatureF": 7430,   # 74.30°F
        "humidity": 6000,       # 60.00%
        "vpdnums": 124,         # 1.24 kPa
        "ports": [
            {"port": 1, "portName": "Intake Fan", "speak": 5, "portsLoad": 1},
            {"port": 2, "portName": "Exhaust Fan", "speak": 7, "portsLoad": 1},
        ],
    },
}


def test_parse_device_data_divide_by_100(client):
    result = client.parse_device_data(MOCK_DEVICE)
    assert result["temperature_c"] == 23.5
    assert result["temperature_f"] == 74.3
    assert result["humidity"] == 60.0
    assert result["vpd"] == 1.24


def test_parse_device_data_device_id(client):
    result = client.parse_device_data(MOCK_DEVICE)
    assert result["device_id"] == "C58ZA"
    assert result["device_name"] == "Test Controller"


def test_parse_device_data_ports(client):
    result = client.parse_device_data(MOCK_DEVICE)
    assert len(result["ports"]) == 2
    assert result["ports"][0]["name"] == "Intake Fan"
    assert result["ports"][0]["speed"] == 5
    assert result["ports"][1]["name"] == "Exhaust Fan"
    assert result["ports"][1]["speed"] == 7


def test_parse_device_data_no_sensors(client):
    result = client.parse_device_data(MOCK_DEVICE)
    assert result["external_sensors"] == []


# ---- parse_history_record ----

def test_parse_history_record_divide_by_100(client):
    record = {
        "createTime": 1714000000,
        "temperature": 2400,
        "fTemperature": 7520,
        "humidity": 5500,
        "vpdNums": 150,  # note: different casing from live data (vpdnums vs vpdNums)
        "portSpead": 0,
        "portStatus": 0,
        "devPortCount": 4,
    }
    result = client.parse_history_record(record)
    assert result["temperature_c"] == 24.0
    assert result["temperature_f"] == 75.2
    assert result["humidity"] == 55.0
    assert result["vpd"] == 1.5


def test_parse_history_record_nibble_decoding(client):
    # Port 1 = speed 5, Port 2 = speed 7, Port 3 = off (0), Port 4 = off
    # nibbles (4 bits each, LSB = port 1): 0x0075
    port_spead = (7 << 4) | 5  # port1=5, port2=7
    record = {
        "createTime": 1714000000,
        "temperature": 0,
        "fTemperature": 0,
        "humidity": 0,
        "vpdNums": 0,
        "portSpead": port_spead,
        "portStatus": 0b11,  # ports 1 and 2 active
        "devPortCount": 4,
    }
    result = client.parse_history_record(record)
    ports = {p["port"]: p for p in result["ports"]}
    assert ports[1]["speed"] == 5
    assert ports[1]["on"] is True
    assert ports[2]["speed"] == 7
    assert ports[2]["on"] is True
    assert ports[3]["speed"] == 0
    assert ports[3]["on"] is False


def test_parse_history_record_toggle_device_oxf(client):
    # 0xF nibble = ON for on/off devices (lights, heaters) — normalise to speed 1
    port_spead = 0xF  # port 1 = 0xF (ON)
    record = {
        "createTime": 1714000000,
        "temperature": 0,
        "fTemperature": 0,
        "humidity": 0,
        "vpdNums": 0,
        "portSpead": port_spead,
        "portStatus": 0,
        "devPortCount": 4,
    }
    result = client.parse_history_record(record)
    assert result["ports"][0]["speed"] == 1


def test_parse_history_record_port_names(client):
    record = {
        "createTime": 1714000000,
        "temperature": 0,
        "fTemperature": 0,
        "humidity": 0,
        "vpdNums": 0,
        "portSpead": 0,
        "portStatus": 0,
        "devPortCount": 2,
    }
    port_names = {1: "Intake Fan", 2: "Exhaust Fan"}
    result = client.parse_history_record(record, port_names=port_names)
    assert result["ports"][0]["name"] == "Intake Fan"
    assert result["ports"][1]["name"] == "Exhaust Fan"


# ---- rate limit enforcement ----

def test_rate_limit_field_exists(client):
    assert hasattr(client, "_last_write_time")
    assert client._last_write_time == 0.0


def test_enforce_write_rate_limit_is_callable(client):
    assert callable(client._enforce_write_rate_limit)
