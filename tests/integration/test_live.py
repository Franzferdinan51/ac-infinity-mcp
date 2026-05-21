"""Live integration tests — skipped in CI without AC_INFINITY_EMAIL credential."""

import asyncio
import json
import os
from datetime import date, timedelta

import pytest

from ac_infinity_mcp import server as srv
from ac_infinity_mcp.client import ACInfinityClient

pytestmark = pytest.mark.skipif(
    not os.getenv("AC_INFINITY_EMAIL"),
    reason="AC_INFINITY_EMAIL not set — skipping live API tests",
)


# ---------------------------------------------------------------------------
# Module-scoped fixtures — authenticate once, reuse across all live tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def authed_client() -> ACInfinityClient:
    email = os.getenv("AC_INFINITY_EMAIL", "")
    password = os.getenv("AC_INFINITY_PASSWORD", "")
    client = ACInfinityClient(email, password)
    assert client.authenticate() is True, "Live authentication failed"
    srv.aci_client = client
    return client


@pytest.fixture(scope="module")
def live_device_id(authed_client: ACInfinityClient) -> str:
    devices = authed_client.get_devices()
    assert devices, "No devices found on live account"
    return str(devices[0]["devCode"])


# ---------------------------------------------------------------------------
# Original 3 tests (preserved)
# ---------------------------------------------------------------------------


def test_live_authenticate(authed_client: ACInfinityClient) -> None:
    # authed_client is already authenticated — verify token is present
    assert authed_client.token is not None


def test_live_get_devices(authed_client: ACInfinityClient) -> None:
    devices = authed_client.get_devices()
    assert devices is not None
    assert len(devices) > 0


def test_live_get_device_reading(authed_client: ACInfinityClient, live_device_id: str) -> None:
    result = asyncio.run(srv.get_device_reading(live_device_id))
    data = json.loads(result)
    assert "temperature_c" in data
    assert "error" not in data


# ---------------------------------------------------------------------------
# Stream B — expanded live tests covering all 11 tools
# ---------------------------------------------------------------------------


def test_live_get_all_device_readings(authed_client: ACInfinityClient) -> None:
    result = asyncio.run(srv.get_all_device_readings())
    data = json.loads(result)
    assert "readings" in data
    assert len(data["readings"]) >= 1
    assert "error" not in data


def test_live_check_vpd_drift_veg(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.check_vpd_drift(live_device_id, "veg"))
    data = json.loads(result)
    assert "current_vpd" in data
    assert data["status"] in {"OK", "LOW", "HIGH"}
    assert len(data["target_range"]) == 2


def test_live_get_environment_health(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.get_environment_health(live_device_id, "veg"))
    data = json.loads(result)
    assert "score" in data
    assert 0 <= data["score"] <= 100
    assert data["grade"] in {"A", "B", "C", "D", "F"}


def test_live_get_historical_readings_1h(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=1)).isoformat()
    result = asyncio.run(
        srv.get_historical_readings(live_device_id, start, end, sample_interval="1h")
    )
    data = json.loads(result)
    assert "readings" in data, f"unexpected response: {data}"
    assert len(data["readings"]) >= 1
    assert "statistics" in data


def test_live_detect_environment_trends(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.detect_environment_trends(live_device_id, days=3))
    data = json.loads(result)
    assert "trends" in data
    for trend in data["trends"]:
        assert "metric" in trend
        assert "slope" in trend
        assert "direction" in trend


def test_live_get_port_activity_report(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.get_port_activity_report(live_device_id, days=3))
    data = json.loads(result)
    assert "ports" in data
    for port in data["ports"]:
        assert "on_hours" in port
        assert "uptime_pct" in port


def test_live_set_port_speed_dry_run(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.set_port_speed(live_device_id, port=1, speed=5, dry_run=True))
    data = json.loads(result)
    assert data.get("dry_run") is True
    assert data.get("sent") is False


def test_live_set_port_on_dry_run(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.set_port_on(live_device_id, port=1, dry_run=True))
    data = json.loads(result)
    assert data.get("dry_run") is True
    assert data.get("sent") is False


def test_live_set_port_off_dry_run(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    result = asyncio.run(srv.set_port_off(live_device_id, port=1, dry_run=True))
    data = json.loads(result)
    assert data.get("dry_run") is True
    assert data.get("sent") is False


def test_live_get_historical_readings_time_filter(
    authed_client: ACInfinityClient, live_device_id: str
) -> None:
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=1)).isoformat()
    result = asyncio.run(
        srv.get_historical_readings(
            live_device_id, start, end, sample_interval="1h",
            time_start="00:00", time_end="23:59",
        )
    )
    data = json.loads(result)
    assert "readings" in data, f"unexpected response: {data}"
