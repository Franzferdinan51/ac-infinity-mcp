"""Controller-type detection and write payload building.

Implements the read-before-write pattern for legacy controllers and
the static-payload pattern for AI+ (new framework) controllers.
Phase 1: stubs only. Full implementation in Phase 8.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ControllerType(Enum):
    LEGACY = "legacy"          # devType 11 (69 Pro), 18 (69 Pro+)
    NEW_FRAMEWORK = "new_framework"  # devType 20+ (89 AI+)


def detect_controller_type(device_data: dict[str, Any]) -> ControllerType:
    """Detect controller type from device data.

    Legacy: devType in {11, 18} or newFrameworkDevice == False
    New framework: devType >= 20 or newFrameworkDevice == True
    """
    dev_type = device_data.get("devType", 0)
    new_framework = device_data.get("newFrameworkDevice", False)

    if new_framework or dev_type >= 20:
        return ControllerType.NEW_FRAMEWORK
    return ControllerType.LEGACY


def build_write_payload(
    current_settings: dict[str, Any],
    updates: dict[str, Any],
    controller_type: ControllerType,
) -> dict[str, Any]:
    """Build the write payload for a port mode/speed change.

    Legacy: deep merge updates into current_settings (all 77 params required).
    New framework: start from static defaults, overlay target fields.
    Phase 8 stub: not yet implemented.
    """
    raise NotImplementedError("build_write_payload is implemented in Phase 8")
