"""Unit tests for ACInfinityClient — data parsing and HTTP methods."""

import pytest
import requests
import responses as responses_lib

from ac_infinity_mcp.client import ACInfinityClient
from tests.fixtures.mock_api_responses import (
    AUTH_FAILURE,
    AUTH_SUCCESS,
    DEVICES_API_ERROR,
    DEVICES_EMPTY,
    DEVICES_SUCCESS,
    HISTORY_EMPTY,
    HISTORY_PAGE_1,
)

LOGIN_URL = "http://www.acinfinityserver.com/api/user/appUserLogin"
DEVICES_URL = "http://www.acinfinityserver.com/api/user/devInfoListAll"
HISTORY_URL = "http://www.acinfinityserver.com/api/log/dataPage"


@pytest.fixture
def client():
    return ACInfinityClient("test@example.com", "password123")


@pytest.fixture
def authed_client():
    c = ACInfinityClient("test@example.com", "password123")
    c.token = "tok_test_abc123"
    return c


# ============ parse_device_data ============

MOCK_DEVICE = {
    "devCode": "C58ZA",
    "devName": "Test Controller",
    "deviceInfo": {
        "temperature": 2350,
        "temperatureF": 7430,
        "humidity": 6000,
        "vpdnums": 124,
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


def test_parse_device_data_with_external_sensors(client):
    device = {
        "devCode": "C58ZA",
        "devName": "Test",
        "deviceInfo": {
            "temperature": 2400,
            "temperatureF": 7520,
            "humidity": 5500,
            "vpdnums": 150,
            "ports": [],
            "sensors": [
                {"accessPort": 1, "sensorType": 11, "sensorData": 85000},
            ],
        },
    }
    result = client.parse_device_data(device)
    assert len(result["external_sensors"]) == 1
    assert result["external_sensors"][0]["sensor_id"] == "1.11"
    assert result["external_sensors"][0]["value"] == pytest.approx(850.0, abs=0.1)


# ============ parse_history_record ============

def test_parse_history_record_divide_by_100(client):
    record = {
        "createTime": 1714000000,
        "temperature": 2400,
        "fTemperature": 7520,
        "humidity": 5500,
        "vpdNums": 150,
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
    port_spead = (7 << 4) | 5  # port1=5, port2=7
    record = {
        "createTime": 1714000000,
        "temperature": 0,
        "fTemperature": 0,
        "humidity": 0,
        "vpdNums": 0,
        "portSpead": port_spead,
        "portStatus": 0b11,
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
    record = {
        "createTime": 1714000000,
        "temperature": 0,
        "fTemperature": 0,
        "humidity": 0,
        "vpdNums": 0,
        "portSpead": 0xF,
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
    result = client.parse_history_record(record, port_names={1: "Intake Fan", 2: "Exhaust Fan"})
    assert result["ports"][0]["name"] == "Intake Fan"
    assert result["ports"][1]["name"] == "Exhaust Fan"


# ============ rate limit ============

def test_rate_limit_field_exists(client):
    assert hasattr(client, "_last_write_time")
    assert client._last_write_time == 0.0


def test_enforce_write_rate_limit_is_callable(client):
    assert callable(client._enforce_write_rate_limit)


# ============ authenticate ============

@responses_lib.activate
def test_authenticate_success(client):
    responses_lib.add(responses_lib.POST, LOGIN_URL, json=AUTH_SUCCESS, status=200)
    result = client.authenticate()
    assert result is True
    assert client.token == "tok_test_abc123"


@responses_lib.activate
def test_authenticate_wrong_credentials(client):
    responses_lib.add(responses_lib.POST, LOGIN_URL, json=AUTH_FAILURE, status=200)
    result = client.authenticate()
    assert result is False
    assert client.token is None


@responses_lib.activate
def test_authenticate_connection_error(client):
    responses_lib.add(
        responses_lib.POST,
        LOGIN_URL,
        body=requests.exceptions.ConnectionError("connection refused"),
    )
    result = client.authenticate()
    assert result is False


@responses_lib.activate
def test_authenticate_timeout(client):
    responses_lib.add(
        responses_lib.POST,
        LOGIN_URL,
        body=requests.exceptions.Timeout("timed out"),
    )
    result = client.authenticate()
    assert result is False


@responses_lib.activate
def test_authenticate_uses_appPasswordl_typo(client):
    responses_lib.add(responses_lib.POST, LOGIN_URL, json=AUTH_SUCCESS, status=200)
    client.authenticate()
    assert len(responses_lib.calls) == 1
    body = responses_lib.calls[0].request.body
    assert "appPasswordl" in body
    assert "appPassword=" not in body


def test_authenticate_password_truncated_to_25_chars():
    c = ACInfinityClient("test@example.com", "a" * 30)
    assert len(c.password) == 25
    assert c.password == "a" * 25


# ============ get_devices ============

@responses_lib.activate
def test_get_devices_success(authed_client):
    responses_lib.add(responses_lib.POST, DEVICES_URL, json=DEVICES_SUCCESS, status=200)
    result = authed_client.get_devices()
    assert result is not None
    assert len(result) == 2


@responses_lib.activate
def test_get_devices_empty(authed_client):
    responses_lib.add(responses_lib.POST, DEVICES_URL, json=DEVICES_EMPTY, status=200)
    result = authed_client.get_devices()
    assert result == []


def test_get_devices_not_authenticated(client):
    result = client.get_devices()
    assert result is None


@responses_lib.activate
def test_get_devices_api_error_code(authed_client):
    responses_lib.add(responses_lib.POST, DEVICES_URL, json=DEVICES_API_ERROR, status=200)
    result = authed_client.get_devices()
    assert result is None


@responses_lib.activate
def test_get_devices_http_error(authed_client):
    responses_lib.add(responses_lib.POST, DEVICES_URL, status=503)
    result = authed_client.get_devices()
    assert result is None


# ============ get_historical_data ============

@responses_lib.activate
def test_get_historical_data_single_page(authed_client):
    responses_lib.add(responses_lib.POST, HISTORY_URL, json=HISTORY_PAGE_1, status=200)
    result = authed_client.get_historical_data(
        dev_id="12345",
        start_timestamp=1714000000,
        end_timestamp=1714086400,
        page_size=2000,
    )
    assert result is not None
    assert len(result) == 10


@responses_lib.activate
def test_get_historical_data_pagination(authed_client):
    base_ts = 1714000000
    page1 = {
        "code": 200,
        "data": {
            "rows": [
                {
                    "createTime": base_ts + i,
                    "temperature": 2400,
                    "fTemperature": 7520,
                    "humidity": 5500,
                    "vpdNums": 150,
                    "portSpead": 0,
                    "portStatus": 0,
                    "devPortCount": 2,
                }
                for i in range(3)
            ]
        },
    }
    page2 = {
        "code": 200,
        "data": {
            "rows": [
                {
                    "createTime": base_ts + 3 + i,
                    "temperature": 2400,
                    "fTemperature": 7520,
                    "humidity": 5500,
                    "vpdNums": 150,
                    "portSpead": 0,
                    "portStatus": 0,
                    "devPortCount": 2,
                }
                for i in range(2)
            ]
        },
    }
    responses_lib.add(responses_lib.POST, HISTORY_URL, json=page1, status=200)
    responses_lib.add(responses_lib.POST, HISTORY_URL, json=page2, status=200)

    result = authed_client.get_historical_data(
        dev_id="12345",
        start_timestamp=base_ts,
        end_timestamp=base_ts + 86400,
        page_size=3,
    )
    assert result is not None
    assert len(result) == 5
    assert len(responses_lib.calls) == 2


@responses_lib.activate
def test_get_historical_data_empty(authed_client):
    responses_lib.add(responses_lib.POST, HISTORY_URL, json=HISTORY_EMPTY, status=200)
    result = authed_client.get_historical_data(
        dev_id="12345", start_timestamp=1714000000, end_timestamp=1714086400
    )
    assert result == []


def test_get_historical_data_not_authenticated(client):
    result = client.get_historical_data(
        dev_id="12345", start_timestamp=1714000000, end_timestamp=1714086400
    )
    assert result is None


@responses_lib.activate
def test_get_historical_data_filters_out_of_range(authed_client):
    base_ts = 1714000000
    payload = {
        "code": 200,
        "data": {
            "rows": [
                # In range
                {"createTime": base_ts + 1, "temperature": 2400, "fTemperature": 7520,
                 "humidity": 5500, "vpdNums": 150, "portSpead": 0, "portStatus": 0,
                 "devPortCount": 2},
                # Out of range (before start)
                {"createTime": base_ts - 1, "temperature": 2400, "fTemperature": 7520,
                 "humidity": 5500, "vpdNums": 150, "portSpead": 0, "portStatus": 0,
                 "devPortCount": 2},
            ]
        },
    }
    responses_lib.add(responses_lib.POST, HISTORY_URL, json=payload, status=200)
    result = authed_client.get_historical_data(
        dev_id="12345",
        start_timestamp=base_ts,
        end_timestamp=base_ts + 86400,
    )
    assert result is not None
    assert len(result) == 1
    assert result[0]["createTime"] == base_ts + 1
