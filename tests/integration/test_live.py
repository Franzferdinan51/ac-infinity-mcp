"""Live integration tests — skipped in CI without AC_INFINITY_EMAIL credential."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("AC_INFINITY_EMAIL"),
    reason="AC_INFINITY_EMAIL not set — skipping live API tests",
)


def test_live_authenticate():
    from ac_infinity_mcp.client import ACInfinityClient

    email = os.getenv("AC_INFINITY_EMAIL", "")
    password = os.getenv("AC_INFINITY_PASSWORD", "")
    client = ACInfinityClient(email, password)
    assert client.authenticate() is True
    assert client.token is not None


def test_live_get_devices():
    from ac_infinity_mcp.client import ACInfinityClient

    email = os.getenv("AC_INFINITY_EMAIL", "")
    password = os.getenv("AC_INFINITY_PASSWORD", "")
    client = ACInfinityClient(email, password)
    client.authenticate()
    devices = client.get_devices()
    assert devices is not None
    assert len(devices) > 0


def test_live_get_device_reading():
    import asyncio
    import json

    from ac_infinity_mcp import server as srv
    from ac_infinity_mcp.client import ACInfinityClient

    email = os.getenv("AC_INFINITY_EMAIL", "")
    password = os.getenv("AC_INFINITY_PASSWORD", "")
    srv.aci_client = ACInfinityClient(email, password)
    srv.aci_client.authenticate()

    devices = srv.aci_client.get_devices()
    assert devices, "No devices found on live account"
    device_id = devices[0]["devCode"]

    result = asyncio.run(srv.get_device_reading(device_id))
    data = json.loads(result)
    assert "temperature_c" in data
    assert "error" not in data
