# AC Infinity API Reference

## Overview

- **Base URL:** `http://www.acinfinityserver.com/api` (HTTP only — see Security Note)
- **Auth:** form-POST to `/user/appUserLogin`; session token returned in `data.appId` field
- **All requests:** `Content-Type: application/x-www-form-urlencoded; charset=utf-8`
- **All responses:** `{"code": 200, "msg": "...", "data": ...}`
- **Non-200 codes** indicate errors (e.g. 400 for bad credentials, 500 for server fault)

## Security Note

The AC Infinity cloud API uses HTTP only (no TLS). This is a known upstream limitation
and is an accepted risk for local/trusted network deployments. See `docs/DEPLOYMENT.md`
for HTTPS reverse-proxy setup options.

Additionally, device list responses include the authenticated user's email address in the
`appEmail` field. Never log raw device API responses at any log level.

---

## Endpoints

### POST /user/appUserLogin

**Purpose:** Authenticate and retrieve a session token.

**Headers:**
```
Content-Type: application/x-www-form-urlencoded; charset=utf-8
User-Agent: ACController/1.8.2 (com.acinfinity.humiture; build:489; iOS 16.5.1)
```

**Request parameters:**

| Field | Type | Notes |
|-------|------|-------|
| `appEmail` | string | User email address |
| `appPasswordl` | string | **Intentional typo — lowercase `l` at end (Quirk 1)** |

**Request example:**
```
appEmail=user%40example.com&appPasswordl=yourpassword
```

**Response (success):**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "appId": "abcdef12...",
    "appEmail": "user@example.com"
  }
}
```

**Response (failure):**
```json
{
  "code": 400,
  "msg": "Email or password is wrong",
  "data": null
}
```

**Notes:**
- Store `data.appId` as the session token for all subsequent requests
- Password is silently truncated to 25 characters server-side (Quirk 2)
- Token does not expire on a fixed TTL in testing; it may expire if the mobile app
  forces a re-login or after extended inactivity. Re-authenticate by restarting the server.

---

### POST /user/devInfoListAll

**Purpose:** Fetch all devices associated with the account.

**Headers:**
```
token: <appId>
Host: www.acinfinityserver.com
User-Agent: okhttp/3.10.0
```

**Query parameters:**
```
userId=<appId>
```

**Response (success):**
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "devId": "9876543210123456789",
      "devCode": "C58ZA",
      "devName": "Towlie Tent",
      "devType": 11,
      "devPortCount": 4,
      "online": 1,
      "newFrameworkDevice": false,
      "firmwareVersion": "3.2.56",
      "hardwareVersion": "1.1",
      "appEmail": "user@example.com",
      "deviceInfo": {
        "temperature": 1803,
        "temperatureF": 6445,
        "humidity": 5895,
        "vpdnums": 78,
        "vpdstatus": 2,
        "ports": [
          {
            "port": 1,
            "portName": "Humidifier",
            "speak": 0,
            "loadType": 0,
            "loadState": 0,
            "online": 0
          },
          {
            "port": 4,
            "portName": "Filter",
            "speak": 5,
            "loadType": 0,
            "loadState": 0,
            "online": 1
          }
        ],
        "sensors": null
      }
    }
  ]
}
```

**Key field notes:**

| Field | Notes |
|-------|-------|
| `devId` | Numeric ID (as string at top level, as integer inside `deviceInfo`). Required by history API. (Quirk 7) |
| `devCode` | Alphanumeric device code (e.g. `"C58ZA"`). Used as `device_id` in MCP tools. (Quirk 7) |
| `online` | `1` = online, `0` = offline |
| `newFrameworkDevice` | `true` for AI+ controllers — use static full payload on write (Quirk 14) |
| `deviceInfo.temperature` | Raw value ÷ 100 = °C (Quirk 4) |
| `deviceInfo.temperatureF` | Raw value ÷ 100 = °F (Quirk 4) |
| `deviceInfo.humidity` | Raw value ÷ 100 = % RH (Quirk 4) |
| `deviceInfo.vpdnums` | Raw value ÷ 100 = VPD in kPa. Note lowercase `n` (Quirk 10) |
| `deviceInfo.ports[].speak` | Port speed 0–10 (Quirk 5 decoding applies in history records, not here) |
| `appEmail` | User's email exposed in every device record — never log raw API responses (Security Note) |

---

### POST /log/dataPage

**Purpose:** Fetch historical sensor and port data for a device.

**Headers:**
```
token: <appId>
Host: www.acinfinityserver.com
User-Agent: okhttp/3.10.0
Content-Type: application/x-www-form-urlencoded; charset=utf-8
```

**Request parameters:**

| Field | Type | Notes |
|-------|------|-------|
| `appId` | string | Session token |
| `devId` | string/int | Numeric device ID from `devInfoListAll.devId` (not `devCode`) |
| `time` | int | Unix timestamp (seconds) — start of window |
| `endTime` | int | Unix timestamp (seconds) — end of window |
| `pageNum` | int | Always send `1` — API ignores this field (Quirk 3) |
| `pageSize` | int | Max records per response. API caps at ~1,257/day regardless (Quirk 9) |

**Request example:**
```
appId=abcdef12...&devId=9876543210123456789&time=1748000000&endTime=1748003600&pageNum=1&pageSize=2000
```

**Response (success):**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "rows": [
      {
        "devId": "9876543210123456789",
        "createTime": 1748000060,
        "temperature": 1796,
        "humidity": 5900,
        "ftemperature": 6433,
        "fTemperature": 6433,
        "vpdNums": 78,
        "vpdnums": 78,
        "portSpead": 0,
        "portStatus": 0,
        "devPortCount": null,
        "allSpead": 0,
        "dataStatus": 0,
        "leafTemp": 0,
        "sensorData": null,
        "sensors": null
      }
    ]
  }
}
```

**Key field notes:**

| Field | Notes |
|-------|-------|
| `createTime` | Unix timestamp of the reading |
| `temperature` | Raw ÷ 100 = °C (Quirk 4) |
| `humidity` | Raw ÷ 100 = % RH (Quirk 4) |
| `fTemperature` | Raw ÷ 100 = °F. Both `ftemperature` and `fTemperature` present — use `fTemperature` (Quirk 4) |
| `vpdNums` | Raw ÷ 100 = VPD. Note uppercase `N` — differs from live device field `vpdnums` (Quirk 10) |
| `portSpead` | Bitmask: 4 bits (one nibble) per port, LSB = Port 1. Values 0–10 = speed; `0xF` (15) = ON for toggle devices (Quirk 5) |
| `portStatus` | Bitmask: 1 bit per port, LSB = Port 1. `1` = port is automation-triggered (Quirk 6) |
| `devPortCount` | Often `null` in history records — fall back to 8 when null (Quirk 5) |

**Pagination strategy:**

The `pageNum` field is ignored by the server (Quirk 3). To retrieve records beyond one
page, use time-cursor pagination:

```python
# After each response, advance the time cursor past the last record
last_ts = rows[-1]["createTime"]
next_request_time = last_ts + 1  # exclusive start for next page
# Stop when: len(rows) < page_size, or last_ts >= end_timestamp
```

---

## All 15 Known API Quirks

### Quirk 1 — Auth typo: `appPasswordl`

The login endpoint parameter for the password is `appPasswordl` — with a lowercase letter
`l` at the end, not the digit `1`. This is an intentional (or permanent) typo in the
AC Infinity app. Using the correct spelling `appPassword` silently fails — the server
accepts the request but returns `code=400`.

**Request field:** `appPasswordl=yourpassword` (not `appPassword`)

---

### Quirk 2 — Password silently truncated to 25 characters

The AC Infinity API silently truncates passwords longer than 25 characters server-side.
Passwords are truncated in the client before sending to ensure consistent authentication
across sessions:

```python
self.password = password[:25]  # applied in ACInfinityClient.__init__
```

---

### Quirk 3 — `pageNum` ignored; use time-cursor pagination

The `pageNum` parameter in `/log/dataPage` is accepted but ignored — the server always
returns the first `pageSize` records starting from `time`. To retrieve subsequent pages,
advance the `time` field past the last returned `createTime`:

```
# Request 1: time=T0, endTime=T1, pageSize=2000
# Response: records [R1...R2000] (newest to oldest)
# Request 2: time=R2000.createTime + 1, endTime=T1, pageSize=2000
# Repeat until response has fewer than pageSize records
```

---

### Quirk 4 — Sensor values divided by 100

All numeric sensor values in API responses are integers representing the actual value × 100.
Divide by 100 to get the real-world value:

| API field | Raw value | Parsed value |
|-----------|-----------|-------------|
| `temperature` | `1803` | `18.03 °C` |
| `temperatureF` | `6445` | `64.45 °F` |
| `humidity` | `5895` | `58.95 % RH` |
| `vpdnums` | `78` | `0.78 kPa` |

---

### Quirk 5 — Port speeds as 4-bit nibbles in `portSpead` bitmask

In historical records, port speeds are packed into the `portSpead` integer field as
4-bit nibbles (one nibble per port). LSB nibble = Port 1:

```python
port_spead = record["portSpead"]  # e.g. 0x0050 = Port1=0, Port2=5
for i in range(port_count):
    nibble = (port_spead >> (i * 4)) & 0xF
    speed = 1 if nibble == 0xF else nibble  # 0xF = ON for toggle devices (lights, heaters)
```

Values 0–10 represent fan/dimmer speed. Value `0xF` (15) represents ON state for
on/off devices (lights, heaters, humidifiers). `devPortCount` is often `null` in
history records — fall back to 8.

---

### Quirk 6 — `portStatus` bitmask (1 bit per port)

The `portStatus` field is a bitmask where each bit indicates whether a port is currently
being triggered by an automation rule (as opposed to manual control):

```python
port_status = record["portStatus"]
for i in range(port_count):
    automation_triggered = bool((port_status >> i) & 1)
```

---

### Quirk 7 — `devCode` (string) ≠ `devId` (numeric)

Every device has two distinct identifiers:

| Field | Example | Used for |
|-------|---------|----------|
| `devCode` | `"C58ZA"` | MCP tool `device_id` parameter; device list display |
| `devId` | `"9876543210123456789"` | History API `devId` parameter |

Passing `devCode` to the history API returns an empty result with no error. Always look
up `devId` from the device list before calling `/log/dataPage`.

Note: `devId` appears as a string at the top level of device records and as a large
integer inside `deviceInfo`. Both represent the same value.

---

### Quirk 8 — HTTP only (no TLS)

The base URL `http://www.acinfinityserver.com/api` uses plain HTTP. The upstream AC
Infinity app does not support HTTPS. Session tokens and sensor data are transmitted
unencrypted. This is an accepted risk for local/trusted network use. See
`docs/DEPLOYMENT.md` for HTTPS reverse-proxy options if exposure is a concern.

---

### Quirk 9 — History API caps at ~1,257 records/day

Regardless of `pageSize`, the `/log/dataPage` endpoint returns at most approximately
1,257 records per calendar day. For multi-day queries the data may appear sparse — this
is a server-side limitation, not a client bug. Expect roughly one record per minute
(1,440/day theoretical maximum, ~1,257 in practice).

---

### Quirk 10 — `vpdnums` (live) vs `vpdNums` (history) casing

The VPD field has different casing in the two contexts:

| Context | Field name | Example |
|---------|-----------|---------|
| Device list (`devInfoListAll`) | `vpdnums` (lowercase `n`) | `"vpdnums": 78` |
| History records (`dataPage`) | `vpdNums` (uppercase `N`) | `"vpdNums": 78` |

Both fields are present in history records (the API returns both `vpdNums` and `vpdnums`),
but only `vpdnums` appears in live device records. Parsers must use the correct field
for each context.

---

### Quirk 11 — Never include `modeSetid` for legacy controllers (→ 403)

When writing mode settings to legacy controllers (where `newFrameworkDevice=false`),
do **not** include the `modeSetid` field in the request payload. Including it causes a
403 error even with a valid token and correct parameters. Omit the field entirely:

```
# BAD  (legacy controller, will 403)
devId=...&modeSetid=0&onSpead=5&...

# GOOD (legacy controller)
devId=...&onSpead=5&...
```

---

### Quirk 12 — Must set `modeType=2` when `onSpead > 0`

When sending a write command with a non-zero fan speed (`onSpead > 0`), the `modeType`
field must be set to `2`. Sending `modeType=0` or omitting it causes the command to
be accepted (200 response) but not persisted — the device reverts to its previous mode.

```
# Required when turning on a port at speed > 0
modeType=2&onSpead=5&...
```

---

### Quirk 13 — Legacy controllers require read-before-write (all 77 params)

Legacy controllers (`newFrameworkDevice=false`) require the full set of ~77 parameters
in every write request to `/dev/addDevMode`. Sending a partial payload results in the
omitted fields being reset to zero/default, which can turn off ports or wipe schedules.

The correct pattern is:
1. Read current mode settings via `GET /dev/getdevModeSettingList`
2. Merge the desired change into the full existing payload
3. Send the complete merged payload to `/dev/addDevMode`

---

### Quirk 14 — AI+ controllers: static full payload

AI+ controllers (`newFrameworkDevice=true`) use a different write API path and accept a
static full payload without a read-before-write step. Detection:

```python
is_ai_plus = device.get("newFrameworkDevice") is True
```

The payload format and endpoint differ from legacy controllers. See Phase 8
implementation notes in `src/ac_infinity_mcp/controller.py`.

---

### Quirk 15 — Rate limit: 1.5s between write calls (→ 403 "Data saving failed")

The AC Infinity API enforces a minimum 1.5-second gap between write API calls. Sending
write requests faster than this returns:

```json
{"code": 403, "msg": "Data saving failed", "data": null}
```

This is enforced in `client.py` via `_enforce_write_rate_limit()`:

```python
def _enforce_write_rate_limit(self) -> None:
    elapsed = time.monotonic() - self._last_write_time
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)
    self._last_write_time = time.monotonic()
```

Read-only calls (`devInfoListAll`, `dataPage`) are not rate-limited.
