import asyncio
import dataclasses
import json
import logging
import os
import re
import sys
from datetime import UTC, datetime, timedelta

from mcp.server.fastmcp import FastMCP

from ac_infinity_mcp.analytics import (
    STAGE_TARGETS,
    build_activity_report,
    calculate_health_score,
    detect_trends,
)
from ac_infinity_mcp.client import ACInfinityClient
from ac_infinity_mcp.schema import (
    ACInfinityAPIError,
    ACInfinityAuthError,
    ACInfinityDeviceError,
    ACIReading,
    VPDTargets,
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

mcp_server = FastMCP(name="ac-infinity-mcp")

# Initialized at startup via main()
aci_client: ACInfinityClient | None = None


def _client() -> ACInfinityClient:
    """Return the initialized client; raises RuntimeError if main() was not called."""
    if aci_client is None:
        raise RuntimeError("AC Infinity client not initialized — call main() first")
    return aci_client


# ============ MCP Tools ============

@mcp_server.tool()
async def discover_devices() -> str:
    """
    Discover all AC Infinity devices from the cloud API.
    Returns device IDs, names, and online status.
    Use this to find device_ids for use in other tools.

    Returns:
        JSON example::

            {
              "devices": [
                {"device_id": "C58ZA", "device_name": "Towlie Tent", "status": "online"},
                {"device_id": "D91XB", "device_name": "Veg Tent",    "status": "online"}
              ]
            }

        Empty account returns ``{"devices": [], "message": "No devices found"}``.
        On failure returns ``{"error": "...", "detail": "..."}``.
    """
    try:
        devices = await asyncio.to_thread(_client().get_devices)
        if not devices:
            return json.dumps({"devices": [], "message": "No devices found"})

        result = [
            {
                "device_id": d.get("devCode"),
                "device_name": d.get("devName"),
                "status": "online" if d.get("online") else "offline",
            }
            for d in devices
        ]

        return json.dumps({"devices": result}, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in discover_devices: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in discover_devices: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in discover_devices: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def get_device_reading(device_id: str) -> str:
    """
    Get current sensor reading for a device by its AC Infinity device_id.
    Returns temperature, humidity, VPD, and timestamp.

    Args:
        device_id: The AC Infinity device code (from discover_devices)

    Returns:
        JSON example::

            {
              "timestamp": "2026-05-20T14:32:00Z",
              "device_id": "C58ZA",
              "device_name": "Towlie Tent",
              "temperature_c": 24.3,
              "temperature_f": 75.7,
              "humidity": 58.2,
              "vpd": 1.31,
              "ports": [
                {"port": 1, "name": "Inline Fan", "speed": 5, "load": 0},
                ...
              ],
              "external_sensors": []
            }

        On failure returns ``{"error": "...", "detail": "..."}``.
    """
    try:
        devices = await asyncio.to_thread(_client().get_devices)

        device = next((d for d in devices if d.get("devCode") == device_id), None)
        if not device:
            return json.dumps({"error": f"Device {device_id} not found"})

        parsed = _client().parse_device_data(device)
        reading = ACIReading(**parsed)

        return json.dumps(reading.to_dict(), indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in get_device_reading: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in get_device_reading: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in get_device_reading: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def get_historical_readings(
    device_id: str,
    start_date: str,
    end_date: str,
    sample_interval: str = "1h",
    time_start: str | None = None,
    time_end: str | None = None,
) -> str:
    """
    Query AC Infinity environment data across a date range with configurable sampling.

    Args:
        device_id: The AC Infinity device code (from discover_devices)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        sample_interval: Bucket size for averaging readings. Use "raw" for all records
            unmodified, or a duration string like "1m", "5m", "15m", "30m", "1h",
            "2h", "6h", "12h", "1d". "daily" is accepted as an alias for "1d".
            Default: "1h" (one averaged reading per hour).
        time_start: Optional UTC time filter in HH:MM format (e.g., "16:00").
            If provided, only readings at or after this time are returned.
        time_end: Optional UTC time filter in HH:MM format (e.g., "16:15").
            If provided, only readings at or before this time are returned.

    Returns:
        JSON with ``"readings"`` list and ``"statistics"`` summary. Each reading contains
        timestamp, temperature_c/f, humidity, vpd, and ports list. Statistics include
        min/avg/max per metric across the returned window. See docs/API.md for full shape.

        On failure returns ``{"error": "...", "detail": "..."}``.
    """
    try:
        try:
            start = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
            end = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
        except ValueError:
            return json.dumps({"error": "Dates must be in YYYY-MM-DD format"})

        if start > end:
            return json.dumps({"error": "start_date must be before or equal to end_date"})

        if sample_interval != "raw":
            try:
                _parse_duration_seconds(sample_interval)
            except ValueError as exc:
                return json.dumps({"error": str(exc)})

        devices = await asyncio.to_thread(_client().get_devices)

        device = next((d for d in devices if d.get("devCode") == device_id), None)
        if not device:
            return json.dumps({"error": f"Device {device_id} not found"})

        import calendar
        start_ts = int(calendar.timegm(start.timetuple()))
        end_ts = int(calendar.timegm(end.replace(hour=23, minute=59, second=59).timetuple()))

        dev_id_numeric = device.get("devId")
        readings: list[dict] = []

        device_info = device.get("deviceInfo", {})
        port_names: dict = {}
        for p in device_info.get("ports", []):
            port_num = p.get("port")
            if port_num is not None:
                port_names[port_num] = p.get("portName", f"Port {port_num}")

        if dev_id_numeric:
            raw_records = await asyncio.to_thread(
                _client().get_historical_data, dev_id_numeric, start_ts, end_ts
            )
            if raw_records:
                readings = [
                    _client().parse_history_record(r, port_names=port_names)
                    for r in raw_records
                ]
                logger.info(
                    "Retrieved %d readings from cloud API for %s", len(readings), device_id
                )

        if not readings:
            return json.dumps({
                "error": (
                    f"No readings available for device {device_id} "
                    f"in range {start_date} to {end_date}"
                ),
            })

        sampled = apply_sampling(readings, sample_interval)

        if time_start or time_end:
            sampled = _filter_readings_by_time(sampled, time_start, time_end)

        if sampled:
            temps_c = [r.get("temperature_c", 0) for r in sampled if "temperature_c" in r]
            temps_f = [r.get("temperature_f", 0) for r in sampled if "temperature_f" in r]
            humidities = [r.get("humidity", 0) for r in sampled if "humidity" in r]
            vpds = [r.get("vpd", 0) for r in sampled if "vpd" in r]

            port_stats: dict = {}
            for r in sampled:
                for port in r.get("ports", []):
                    name = port.get("name", f"Port {port.get('port')}")
                    port_stats.setdefault(name, []).append(port.get("speed", 0))

            port_statistics = {
                name: {
                    "min": round(min(speeds), 2),
                    "avg": round(sum(speeds) / len(speeds), 2),
                    "max": round(max(speeds), 2),
                }
                for name, speeds in sorted(port_stats.items())
                if any(s > 0 for s in speeds)
            }

            stats = {
                "readings_count": len(sampled),
                "sample_interval": sample_interval,
                "date_range": {"start": start_date, "end": end_date},
                "temperature_c": {
                    "min": round(min(temps_c), 2) if temps_c else None,
                    "avg": round(sum(temps_c) / len(temps_c), 2) if temps_c else None,
                    "max": round(max(temps_c), 2) if temps_c else None,
                },
                "temperature_f": {
                    "min": round(min(temps_f), 2) if temps_f else None,
                    "avg": round(sum(temps_f) / len(temps_f), 2) if temps_f else None,
                    "max": round(max(temps_f), 2) if temps_f else None,
                },
                "humidity": {
                    "min": round(min(humidities), 2) if humidities else None,
                    "avg": round(sum(humidities) / len(humidities), 2) if humidities else None,
                    "max": round(max(humidities), 2) if humidities else None,
                },
                "vpd": {
                    "min": round(min(vpds), 2) if vpds else None,
                    "avg": round(sum(vpds) / len(vpds), 2) if vpds else None,
                    "max": round(max(vpds), 2) if vpds else None,
                },
                "port_statistics": port_statistics,
            }
        else:
            stats = {"error": "No data available after sampling"}

        return json.dumps({
            "device_id": device_id,
            "readings": sampled,
            "statistics": stats,
        }, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in get_historical_readings: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in get_historical_readings: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in get_historical_readings: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def check_vpd_drift(device_id: str, stage: str = "veg") -> str:
    """
    Check if current VPD is within target range for a growth stage.

    Args:
        device_id: The AC Infinity device code (from discover_devices)
        stage: Growth stage - one of: clones, seedling, veg, early_flower, mid_flower, late_flower

    Returns:
        JSON example::

            {
              "device_id": "C58ZA",
              "current_vpd": 1.58,
              "target_range": [1.0, 1.5],
              "stage": "veg",
              "status": "HIGH",
              "alert": "VPD 1.58 exceeds target 1.00-1.50. Increase circulation."
            }

        ``status`` is one of ``"OK"``, ``"LOW"``, or ``"HIGH"``.
        ``alert`` is ``null`` when status is ``"OK"``.
        On failure returns ``{"error": "...", "detail": "..."}``.
    """
    try:
        reading_json = await get_device_reading(device_id)
        reading = json.loads(reading_json)

        if "error" in reading:
            return json.dumps(reading)

        targets = VPDTargets()
        target_range = getattr(targets, stage, targets.veg)
        current_vpd = reading["vpd"]

        status = "OK"
        alert = None

        if current_vpd < target_range[0]:
            status = "LOW"
            alert = (
                f"VPD {current_vpd:.2f} is below target "
                f"{target_range[0]:.2f}–{target_range[1]:.2f}. "
                "Lower fan speed or increase humidity."
            )
        elif current_vpd > target_range[1]:
            status = "HIGH"
            alert = (
                f"VPD {current_vpd:.2f} exceeds target "
                f"{target_range[0]:.2f}–{target_range[1]:.2f}. "
                "Increase air circulation or reduce humidity."
            )

        return json.dumps({
            "device_id": device_id,
            "current_vpd": current_vpd,
            "target_range": target_range,
            "stage": stage,
            "status": status,
            "alert": alert,
        }, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in check_vpd_drift: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in check_vpd_drift: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in check_vpd_drift: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def get_all_device_readings() -> str:
    """
    Get current sensor readings for all AC Infinity devices.
    Useful for a full status check across all controllers.
    Returns a list of readings keyed by device_id.

    Returns:
        JSON with ``"readings"`` list — one entry per device, same shape as
        ``get_device_reading``. Devices that fail to parse individually include
        an ``"error"`` key instead of sensor fields.
        On auth/API failure returns ``{"error": "...", "detail": "..."}``.
    """
    try:
        devices = await asyncio.to_thread(_client().get_devices)

        readings = []
        for device in devices:
            device_id = device.get("devCode")
            try:
                parsed = _client().parse_device_data(device)
                reading = ACIReading(**parsed)
                readings.append({
                    "device_id": device_id,
                    "device_name": device.get("devName"),
                    **reading.to_dict(),
                })
            except Exception as e:
                readings.append({
                    "device_id": device_id,
                    "device_name": device.get("devName"),
                    "error": str(e),
                })

        return json.dumps({"readings": readings}, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in get_all_device_readings: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in get_all_device_readings: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in get_all_device_readings: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def get_environment_health(device_id: str, stage: str = "veg") -> str:
    """
    Calculate composite environment health score (0–100) for a device.

    Args:
        device_id: The AC Infinity device code (from discover_devices)
        stage: Growth stage — one of: clones, seedling, veg,
               early_flower, mid_flower, late_flower. Default: veg.

    Returns:
        JSON with score (0–100), grade (A–F), per-metric sub-scores,
        and a top actionable recommendation.
    """
    try:
        if stage not in STAGE_TARGETS:
            valid = ", ".join(STAGE_TARGETS)
            return json.dumps({"error": f"Unknown stage: {stage}. Valid: {valid}"})

        reading_json = await get_device_reading(device_id)
        reading = json.loads(reading_json)
        if "error" in reading:
            return json.dumps(reading)

        health = calculate_health_score(reading, stage)
        result = dataclasses.asdict(health)
        result["device_id"] = device_id
        result["stage"] = stage
        return json.dumps(result, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in get_environment_health: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in get_environment_health: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in get_environment_health: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def detect_environment_trends(device_id: str, days: int = 7) -> str:
    """
    Detect linear trends in temperature, humidity, and VPD over a look-back window.

    Args:
        device_id: The AC Infinity device code (from discover_devices)
        days: Number of days to look back. Default: 7. Must be 1–30.

    Returns:
        JSON with per-metric trend reports: slope (change/hour), direction,
        7-day projection, and alert flag.

    Note:
        The AC Infinity history API returns a maximum of ~1257 records per day
        regardless of page_size. For longer windows the data may be sparse.
    """
    try:
        if not 1 <= days <= 30:
            return json.dumps({"error": "days must be between 1 and 30"})

        today = datetime.utcnow()
        start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        hist_json = await get_historical_readings(device_id, start_date, end_date, "1h")
        hist = json.loads(hist_json)
        if "error" in hist:
            return json.dumps(hist)

        readings = hist.get("readings", [])
        trends = detect_trends(readings, days)

        return json.dumps({
            "device_id": device_id,
            "days_analyzed": days,
            "readings_used": len(readings),
            "trends": [dataclasses.asdict(t) for t in trends],
        }, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in detect_environment_trends: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in detect_environment_trends: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in detect_environment_trends: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def get_port_activity_report(device_id: str, days: int = 7) -> str:
    """
    Build a per-port runtime activity report from historical data.

    Args:
        device_id: The AC Infinity device code (from discover_devices)
        days: Number of days to analyze. Default: 7. Must be 1–30.

    Returns:
        JSON with per-port on_hours, off_hours, transitions, avg_speed_when_running,
        uptime_pct, and peak_hour (UTC).
    """
    try:
        if not 1 <= days <= 30:
            return json.dumps({"error": "days must be between 1 and 30"})

        today = datetime.utcnow()
        start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        hist_json = await get_historical_readings(device_id, start_date, end_date, "raw")
        hist = json.loads(hist_json)
        if "error" in hist:
            return json.dumps(hist)

        readings = hist.get("readings", [])
        ports = build_activity_report(readings)

        return json.dumps({
            "device_id": device_id,
            "days_analyzed": days,
            "readings_used": len(readings),
            "ports": [dataclasses.asdict(p) for p in ports],
        }, indent=2)

    except ACInfinityAuthError as e:
        logger.warning("Auth error in get_port_activity_report: %s", e)
        return json.dumps({
            "error": "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD",
            "detail": str(e),
        })
    except ACInfinityAPIError as e:
        logger.error("API error in get_port_activity_report: %s", e)
        return json.dumps({"error": "AC Infinity API error", "detail": str(e)})
    except Exception as e:
        logger.error("Unexpected error in get_port_activity_report: %s", e)
        return json.dumps({"error": str(e)})


# ============ Write Tools ============

@mcp_server.tool()
async def set_port_speed(
    device_id: str,
    port: int,
    speed: int,
    dry_run: bool = True,
) -> str:
    """Set fan or dimmer speed on a specific port.

    Uses read-before-write: reads current mode settings then overlays the new
    speed value. Defaults to dry_run=True — set dry_run=False to write to the
    device.

    Args:
        device_id: Device code from discover_devices (e.g. "C58ZA").
        port: 1-based port number.
        speed: Target speed 1–10 (10 = full speed).
        dry_run: If True (default), returns the payload that would be sent
            without writing. Set to False to execute the change.

    Returns:
        JSON with action, device_id, port, speed, dry_run, controller_type,
        sent, and payload (when dry_run=True).

        Example (dry_run=True)::

            {
              "action": "set port 2 speed to 5",
              "device_id": "C58ZA",
              "port": 2,
              "speed": 5,
              "dry_run": true,
              "controller_type": "legacy",
              "sent": false,
              "payload": { ... }
            }

        On failure returns ``{"error": "..."}``.
    """
    try:
        if port < 1:
            return json.dumps({"error": "port must be a positive integer"})
        if not 1 <= speed <= 10:
            return json.dumps({"error": "speed must be 1–10"})

        devices = await asyncio.to_thread(_client().get_devices)
        device = next((d for d in devices if d.get("devCode") == device_id), None)
        if not device:
            return json.dumps({"error": f"Device {device_id} not found"})

        write_result = await asyncio.to_thread(
            _client().set_port_mode, device, port, {"onSpead": speed}, dry_run
        )

        response: dict = {
            "action": f"set port {port} speed to {speed}",
            "device_id": device_id,
            "port": port,
            "speed": speed,
            "dry_run": write_result["dry_run"],
            "controller_type": write_result["controller_type"],
            "sent": write_result["sent"],
        }
        if write_result["dry_run"]:
            response["payload"] = write_result["payload"]

        return json.dumps(response, indent=2)

    except (ACInfinityAuthError, ACInfinityAPIError, ACInfinityDeviceError) as e:
        logger.warning("Error in set_port_speed (device=%s port=%s): %s", device_id, port, e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error("Unexpected error in set_port_speed: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def set_port_on(
    device_id: str,
    port: int,
    dry_run: bool = True,
) -> str:
    """Turn a port on at full speed (onSpead=10).

    Works for fan-type and on/off toggle devices. Uses read-before-write.
    Defaults to dry_run=True — set dry_run=False to write to the device.

    Args:
        device_id: Device code from discover_devices (e.g. "C58ZA").
        port: 1-based port number.
        dry_run: If True (default), returns the payload that would be sent
            without writing.

    Returns:
        JSON with action, device_id, port, dry_run, controller_type, sent,
        and payload (when dry_run=True). On failure returns ``{"error": "..."}``.
    """
    try:
        if port < 1:
            return json.dumps({"error": "port must be a positive integer"})

        devices = await asyncio.to_thread(_client().get_devices)
        device = next((d for d in devices if d.get("devCode") == device_id), None)
        if not device:
            return json.dumps({"error": f"Device {device_id} not found"})

        write_result = await asyncio.to_thread(
            _client().set_port_mode, device, port, {"onSpead": 10}, dry_run
        )

        response: dict = {
            "action": f"turn port {port} on",
            "device_id": device_id,
            "port": port,
            "dry_run": write_result["dry_run"],
            "controller_type": write_result["controller_type"],
            "sent": write_result["sent"],
        }
        if write_result["dry_run"]:
            response["payload"] = write_result["payload"]

        return json.dumps(response, indent=2)

    except (ACInfinityAuthError, ACInfinityAPIError, ACInfinityDeviceError) as e:
        logger.warning("Error in set_port_on (device=%s port=%s): %s", device_id, port, e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error("Unexpected error in set_port_on: %s", e)
        return json.dumps({"error": str(e)})


@mcp_server.tool()
async def set_port_off(
    device_id: str,
    port: int,
    dry_run: bool = True,
) -> str:
    """Turn a port off (onSpead=0).

    Uses read-before-write. Defaults to dry_run=True — set dry_run=False to
    write to the device.

    Args:
        device_id: Device code from discover_devices (e.g. "C58ZA").
        port: 1-based port number.
        dry_run: If True (default), returns the payload that would be sent
            without writing.

    Returns:
        JSON with action, device_id, port, dry_run, controller_type, sent,
        and payload (when dry_run=True). On failure returns ``{"error": "..."}``.
    """
    try:
        if port < 1:
            return json.dumps({"error": "port must be a positive integer"})

        devices = await asyncio.to_thread(_client().get_devices)
        device = next((d for d in devices if d.get("devCode") == device_id), None)
        if not device:
            return json.dumps({"error": f"Device {device_id} not found"})

        write_result = await asyncio.to_thread(
            _client().set_port_mode, device, port, {"onSpead": 0}, dry_run
        )

        response: dict = {
            "action": f"turn port {port} off",
            "device_id": device_id,
            "port": port,
            "dry_run": write_result["dry_run"],
            "controller_type": write_result["controller_type"],
            "sent": write_result["sent"],
        }
        if write_result["dry_run"]:
            response["payload"] = write_result["payload"]

        return json.dumps(response, indent=2)

    except (ACInfinityAuthError, ACInfinityAPIError, ACInfinityDeviceError) as e:
        logger.warning("Error in set_port_off (device=%s port=%s): %s", device_id, port, e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error("Unexpected error in set_port_off: %s", e)
        return json.dumps({"error": str(e)})


# ============ Helpers ============

_DURATION_RE = re.compile(r"^(\d+)(m|h|d)$", re.IGNORECASE)
_DURATION_UNITS = {"m": 60, "h": 3600, "d": 86400}


def _parse_duration_seconds(interval: str) -> int:
    """Parse a duration string into a bucket size in seconds.

    Accepts e.g. "1m", "5m", "15m", "30m", "1h", "2h", "6h", "12h", "1d".
    "daily" is accepted as an alias for "1d".
    Raises ValueError for unrecognised formats.
    """
    if interval in ("daily", "1d"):
        return 86400
    m = _DURATION_RE.fullmatch(interval)
    if not m:
        raise ValueError(
            f"Invalid sample_interval {interval!r}. "
            "Use 'raw' for unsampled data, or a duration like '1m', '5m', '15m', "
            "'30m', '1h', '2h', '6h', '12h', '1d'."
        )
    value, unit = int(m.group(1)), m.group(2).lower()
    return value * _DURATION_UNITS[unit]


def _filter_readings_by_time(
    readings: list, time_start: str | None = None, time_end: str | None = None
) -> list:
    """Filter readings to only include those within a UTC time window (HH:MM format)."""
    if not time_start and not time_end:
        return readings

    filtered = []
    for reading in readings:
        timestamp_str = reading.get("timestamp", "")
        try:
            ts_dt = datetime.fromisoformat(timestamp_str.rstrip("Z").replace("+00:00", ""))
            ts_dt = ts_dt.replace(tzinfo=UTC)
            reading_time = ts_dt.strftime("%H:%M")

            include = True
            if time_start and reading_time < time_start:
                include = False
            if time_end and reading_time > time_end:
                include = False

            if include:
                filtered.append(reading)
        except Exception as e:
            logger.warning("Could not parse timestamp %s: %s", timestamp_str, e)
            continue

    return filtered


def apply_sampling(readings: list, interval: str) -> list:
    """Bucket readings by the given duration interval and average each bucket.

    "raw" returns all records unchanged.
    Any duration string (e.g. "1m", "15m", "1h", "6h", "1d") averages readings
    into fixed-width time buckets of that size; each bucket is represented by
    a single averaged record whose timestamp is the bucket-start time (UTC).
    """
    if interval == "raw":
        return readings

    bucket_secs = _parse_duration_seconds(interval)
    sampled: dict = {}

    for reading in readings:
        timestamp_str = reading.get("timestamp", "")
        try:
            ts_dt = datetime.fromisoformat(timestamp_str.rstrip("Z"))
            unix_ts = int(ts_dt.replace(tzinfo=UTC).timestamp())
        except Exception:
            continue
        bucket_key = (unix_ts // bucket_secs) * bucket_secs
        sampled.setdefault(bucket_key, []).append(reading)

    result = []
    for bucket_key in sorted(sampled.keys()):
        avg = average_readings(sampled[bucket_key])
        avg["timestamp"] = datetime.utcfromtimestamp(bucket_key).isoformat() + "Z"
        result.append(avg)
    return result


def average_readings(readings: list) -> dict:
    """Compute average of multiple readings."""
    if not readings:
        return {}

    temps_c = [r.get("temperature_c", 0) for r in readings]
    temps_f = [r.get("temperature_f", 0) for r in readings]
    humidities = [r.get("humidity", 0) for r in readings]
    vpds = [r.get("vpd", 0) for r in readings]

    ports_by_number: dict = {}
    for reading in readings:
        for port in reading.get("ports", []):
            port_num = port.get("port")
            if port_num not in ports_by_number:
                ports_by_number[port_num] = {
                    "port": port_num,
                    "name": port.get("name", f"Port {port_num}"),
                    "speeds": [],
                    "on_count": 0,
                }
            ports_by_number[port_num]["speeds"].append(port.get("speed", 0))
            if port.get("on"):
                ports_by_number[port_num]["on_count"] += 1

    averaged_ports = [
        {
            "port": port_num,
            "name": data["name"],
            "speed": round(sum(data["speeds"]) / len(data["speeds"]), 2),
            "on": data["on_count"] > 0,
        }
        for port_num, data in sorted(ports_by_number.items())
    ]

    return {
        "timestamp": readings[0].get("timestamp"),
        "temperature_c": round(sum(temps_c) / len(temps_c), 2) if temps_c else None,
        "temperature_f": round(sum(temps_f) / len(temps_f), 2) if temps_f else None,
        "humidity": round(sum(humidities) / len(humidities), 2) if humidities else None,
        "vpd": round(sum(vpds) / len(vpds), 2) if vpds else None,
        "ports": averaged_ports,
    }


def main() -> None:
    email = os.getenv("AC_INFINITY_EMAIL")
    password = os.getenv("AC_INFINITY_PASSWORD")

    if not email or not password:
        logger.error(
            "Missing AC_INFINITY_EMAIL or AC_INFINITY_PASSWORD — set in .env"
        )
        sys.exit(1)

    global aci_client
    aci_client = ACInfinityClient(email, password)
    if not aci_client.authenticate():
        logger.error("Failed to authenticate with AC Infinity")
        sys.exit(1)

    async def _run() -> None:
        logger.info("AC Infinity MCP Server ready (stdio)")
        await mcp_server.run_stdio_async()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
