"""Analytics: health scoring, trend detection, activity reporting.

Pure functions — no API calls. All data comes from client.py responses.
Phase 1: stubs only. Full implementation in Phase 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HealthScore:
    score: float
    grade: str
    vpd_score: float
    temp_score: float
    humidity_score: float
    top_recommendation: str


@dataclass
class TrendReport:
    metric: str
    slope: float
    direction: str
    seven_day_projection: float
    alert: bool


@dataclass
class ActivityReport:
    port: int
    name: str
    on_hours: float
    off_hours: float
    transitions: int
    avg_speed_when_running: float
    uptime_pct: float
    peak_hour: int


def calculate_health_score(reading: dict[str, Any], stage: str) -> HealthScore:
    """Calculate composite 0-100 env health score. Phase 7 stub."""
    raise NotImplementedError("calculate_health_score is implemented in Phase 7")


def detect_trends(readings: list[dict[str, Any]], days: int) -> list[TrendReport]:
    """Detect linear trends in historical readings. Phase 7 stub."""
    raise NotImplementedError("detect_trends is implemented in Phase 7")


def build_activity_report(readings: list[dict[str, Any]]) -> list[ActivityReport]:
    """Build per-port runtime activity report. Phase 9 stub."""
    raise NotImplementedError("build_activity_report is implemented in Phase 9")
