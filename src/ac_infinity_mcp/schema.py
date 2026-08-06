import math

# ============ Custom Exception Classes ============

class ACInfinityError(Exception):
    """Base exception for AC Infinity integration."""
    pass


class ACInfinityAuthError(ACInfinityError):
    """Authentication failure with AC Infinity API."""
    pass


class ACInfinityAPIError(ACInfinityError):
    """API communication error."""
    pass


class ACInfinityDeviceError(ACInfinityError):
    """Device not found or invalid."""
    pass


class ACInfinityAdvanceConflictError(ACInfinityDeviceError):
    """Raised when a write targets a port under Advance Automation control (modeType=15)."""
    pass


class ACInfinityConfigError(ACInfinityError):
    """Configuration or file error."""
    pass


# Single source of truth for the auth-failure message returned to the MCP client.
# Lives here (the shared leaf module) so every tool in server.py AND the conflict
# helper in automation.py emit identical wording. The 25-character note surfaces
# Quirk 2 (the API silently truncates longer passwords) to growers, who typically
# don't watch server logs and so never see the operator-facing warning from
# client.py. AC_INFINITY_EMAIL/PASSWORD are env-var names the self-hosting grower
# sets themselves — safe to name; no credential value is included.
_AUTH_ERROR_MSG = (
    "Authentication failed — check AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD "
    "(note: AC Infinity passwords are limited to 25 characters; longer ones are "
    "truncated and login will fail)"
)


# Timeout error for write operations. The AC Infinity server may have processed the
# write before the timeout, so we do NOT retry to avoid double-applying state.
# The caller should check the device manually and retry only after verifying the
# current state — a second write to an already-applied command could cause issues.
_WRITE_TIMEOUT_MSG = (
    "The request timed out waiting for the AC Infinity server to respond. "
    "The server may have processed the change before the timeout, so I have not "
    "retried to avoid double-applying state. Please check your device to verify "
    "the current state, then retry with dry_run=False if needed."
)


# ============ Advance Automation Constants ============

# modeType value that indicates a port is under Advance Automation control.
# Writing to a port in this mode returns API code 999999.
_ADVANCE_MODE_TYPE: int = 15

# Live-tested (2026-05-22): disabling an Advance Automation sets governed ports
# to OFF (mode=OFF, power_level=0); re-enabling immediately restores them to
# ADVANCE mode at the automation-defined speeds — no next-trigger wait required.
# Used in disable_advance_automation and break_out_of_automation tool responses.
ADVANCE_REVERT_BEHAVIOR_CONFIRMED: bool = True


def calculate_vpd(temp_c: float, humidity: float) -> float:
    """Calculate VPD using Magnus formula"""
    a = 17.27
    b = 237.7
    alpha = (a * temp_c) / (b + temp_c)
    svp = 0.6108 * math.exp(alpha)
    vpd = svp * (1 - humidity / 100.0)
    return round(vpd, 2)
