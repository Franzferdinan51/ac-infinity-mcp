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

### POST /dev/getdevModeSettingList

**Purpose:** Read current mode settings for one port on a device (required before every legacy write).

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
| `devId` | string | Numeric device ID from `devInfoListAll` (Quirk 7) |
| `port` | int | 1-based port number. **Required** — omitting returns code 999999 (Quirk 16) |
| `appId` | string | Session token (`appId` from login) |

**Request example:**
```
devId=REDACTED_DEV_ID&port=1&appId=REDACTED_TOKEN
```

**Response (success):**
```json
{
  "code": 200,
  "msg": "success.",
  "data": {
    "modeSetid": "REDACTED_MODE_SET_ID",
    "devId": "REDACTED_DEV_ID",
    "externalPort": 1,
    "offSpead": 0,
    "onSpead": 5,
    "onSelfSpead": 0,
    "activeHt": 0,
    "devHt": 90,
    "devHtf": 194,
    "devLtf": 32,
    "activeLt": 0,
    "devLt": 0,
    "activeHh": 0,
    "devHh": 100,
    "activeLh": 0,
    "devLh": 0,
    "acitveTimerOn": 0,
    "acitveTimerOff": 0,
    "activeCycleOn": 300,
    "activeCycleOff": 60,
    "schedStartTime": 65535,
    "schedEndtTime": 65535,
    "surplus": 0,
    "modeType": 0,
    "activeHtVpd": 0,
    "activeLtVpd": 0,
    "activeHtVpdNums": 99,
    "activeLtVpdNums": 1,
    "targetTSwitch": 0,
    "targetHumiSwitch": 0,
    "settingMode": 0,
    "vpdSettingMode": 0,
    "targetVpdSwitch": 0,
    "targetVpd": 0,
    "targetTemp": 0,
    "targetTempF": 32,
    "targetHumi": 65,
    "isUpdateVpdNums": false,
    "co2TargetSwitch": 0,
    "co2SettingMode": 0,
    "co2HighSwitch": 0,
    "co2LowSwitch": 0,
    "co2HighValue": 0,
    "co2LowValue": 0,
    "co2TargetValue": 0,
    "co2Accuracy": 0,
    "co2FanTargetSwitch": 0,
    "co2FanSettingMode": 0,
    "co2FanHighSwitch": 0,
    "co2FanLowSwitch": 0,
    "co2FanHighValue": 0,
    "co2FanLowValue": 0,
    "co2FanTargetValue": 0,
    "co2FanAccuracy": 0,
    "moistureTargetSwitch": 0,
    "moistureSettingMode": 0,
    "moistureHighSwitch": 0,
    "moistureLowSwitch": 0,
    "moistureHighValue": 0,
    "moistureLowValue": 0,
    "moistureTargetValue": 0,
    "moistureAccuracy": 0,
    "waterTempTargetSwitch": 0,
    "waterTempSettingMode": 0,
    "waterTempHighSwitch": 0,
    "waterTempLowSwitch": 0,
    "waterTempHighValueF": 32,
    "waterTempHighValue": 0,
    "waterTempLowValueF": 32,
    "waterTempLowValue": 0,
    "waterTempTargetValueF": 32,
    "waterTempTargetValue": 0,
    "waterTempAccuracy": 0,
    "phTargetSwitch": 0,
    "phSettingMode": 0,
    "phHighSwitch": 0,
    "phLowSwitch": 0,
    "phHighValue": 0,
    "phLowValue": 0,
    "phTargetValue": 0,
    "phAccuracy": 0,
    "ecTdsTargetSwitch": 0,
    "ecTdsSettingMode": 0,
    "ecTdsHighSwitch": 0,
    "ecTdsLowSwitchEc": 0,
    "ecTdsLowSwitchTds": 0,
    "ecTdsHighValueEcUs": 0,
    "ecTdsHighValueEcMs": 0,
    "ecTdsHighValueTdsPpm": 0,
    "ecTdsHighValueTdsPpt": 0,
    "ecTdsLowValueEcUs": 0,
    "ecTdsLowValueEcMs": 0,
    "ecTdsLowValueTdsPpm": 0,
    "ecTdsLowValueTdsPpt": 0,
    "ecTdsTargetValueEcUs": 0,
    "ecTdsTargetValueEcMs": 0,
    "ecTdsTargetValueTdsPpm": 0,
    "ecTdsTargetValueTdsPpt": 0,
    "ecTdsAccuracy": 0,
    "waterLevelTargetSwitch": 0,
    "waterLevelSettingMode": 0,
    "waterLevelHighSwitch": 0,
    "waterLevelLowSwitch": 0,
    "waterLevelHighValue": 0,
    "waterLevelLowValue": 0,
    "waterLevelTargetValue": 0,
    "waterLevelAccuracy": 0,
    "ecOrTds": null,
    "flowRate": null,
    "quickRunTime": null,
    "quickRunState": null,
    "sensorModeFlowRate": null,
    "maxWateringAmount": null,
    "protection": null,
    "schedModeFlowRate": null,
    "waterDuration": 0,
    "interval": 0,
    "timestamp": null,
    "reportSeq": null,
    "fieldSet": [],
    "humidity": 5714,
    "temperature": 1792,
    "tTrend": 0,
    "hTrend": 0,
    "unit": 0,
    "speak": 0,
    "trend": 0,
    "atType": 1,
    "temperatureF": 6426,
    "isOpenAutomation": 0,
    "devTimeZone": null,
    "loadType": 0,
    "loadState": 0,
    "abnormalState": 0,
    "devMacAddr": null,
    "restore": false,
    "masterPort": null,
    "onlyUpdateSpeed": 0,
    "tdsUnit": 0,
    "ecUnit": 0,
    "devSetting": { "...": "nested device config — not included in write payload" },
    "ipcSetting": null
  }
}
```

**Structure notes:**

| Aspect | Detail |
|--------|--------|
| Total fields | 142 per port response |
| Flat scalar fields | 140 (these form the write payload basis) |
| `fieldSet` | Always `[]` — exclude from write payload (Quirk 13) |
| `devSetting` | Nested device config dict — exclude from write payload (Quirk 13) |
| `ipcSetting` | Always `null` — exclude from write payload |
| Response vs legacy vs AI+ | Identical 142-field structure for devType 11, 18, and 22 |

**Field reference (140 flat fields):**

| Field | Type | Description |
|-------|------|-------------|
| `modeSetid` | string | Record ID — **exclude from write payload** (Quirk 11) |
| `devId` | string | Device ID — include in write payload |
| `externalPort` | int | Port number (1-based) |
| `offSpead` | int | Off speed (0–10) |
| `onSpead` | int | On speed (0–10) |
| `onSelfSpead` | int | Self-start speed |
| `modeType` | int | Mode type — must be 2 when `onSpead > 0` (Quirk 12) |
| `activeHt` / `activeHh` / `activeLt` / `activeLh` | int | High/low temp/humidity trigger enables |
| `devHt` / `devHtf` / `devLt` / `devLtf` | int | High/low temp thresholds (°C and °F) |
| `devHh` / `devLh` | int | High/low humidity thresholds |
| `acitveTimerOn` / `acitveTimerOff` | int | Timer enable flags (note typo in field name) |
| `activeCycleOn` / `activeCycleOff` | int | Cycle mode on/off durations (seconds) |
| `schedStartTime` / `schedEndtTime` | int | Schedule start/end (65535 = disabled; note typo in `schedEndtTime`) |
| `surplus` | int or null | Legacy: 0; AI+: null |
| `activeHtVpd` / `activeLtVpd` | int | VPD high/low trigger enables |
| `activeHtVpdNums` / `activeLtVpdNums` | int | VPD thresholds |
| `targetTSwitch` / `targetHumiSwitch` / `targetVpdSwitch` | int | Target mode enables |
| `settingMode` / `vpdSettingMode` | int | Setting mode flags |
| `targetVpd` / `targetTemp` / `targetTempF` / `targetHumi` | int | Target values |
| `isUpdateVpdNums` | bool | VPD update flag |
| `co2*` / `co2Fan*` | int | CO2 and CO2 fan automation settings (8 fields each) |
| `moisture*` | int | Moisture sensor automation settings (8 fields) |
| `waterTemp*` | int | Water temperature automation settings (11 fields) |
| `ph*` | int | pH automation settings (8 fields) |
| `ecTds*` | int | EC/TDS automation settings (17 fields) |
| `waterLevel*` | int | Water level automation settings (8 fields) |
| `waterDuration` / `interval` | int | Watering duration and interval |
| `humidity` / `temperature` / `temperatureF` | int | Current sensor readings (raw ×100) — included in write payload |
| `speak` / `trend` / `tTrend` / `hTrend` | int | Current port/trend state |
| `atType` / `unit` | int | Automation type / unit flags |
| `isOpenAutomation` | int | Automation enabled flag |
| `loadType` / `loadState` / `abnormalState` | int | Port load info |
| `restore` | bool | Restore flag |
| `onlyUpdateSpeed` / `tdsUnit` / `ecUnit` | int | Misc flags |
| Null fields | — | `ecOrTds`, `flowRate`, `quickRunTime`, `quickRunState`, `sensorModeFlowRate`, `maxWateringAmount`, `protection`, `schedModeFlowRate`, `timestamp`, `reportSeq`, `devTimeZone`, `devMacAddr`, `masterPort` |

---

### POST /dev/addDevMode

**Purpose:** Write mode settings for one port. Used by both legacy and AI+ controllers.

**Critical:** Strip `modeSetid` (Quirk 11). Set `modeType=2` when `onSpead > 0` (Quirk 12).
Enforce 1.5s minimum between calls (Quirk 15).

**Headers:** Same as `getdevModeSettingList`.

**Request parameters:** All 140 flat scalar fields from `getdevModeSettingList` response,
with `modeSetid` removed and desired changes overlaid. Do **not** include `fieldSet` (list)
or `devSetting` (nested dict) — these cannot be form-encoded.

**Request example (partial):**
```
devId=REDACTED_DEV_ID&externalPort=1&onSpead=5&modeType=2&offSpead=0&...
```

**Response (success):**
```json
{"code": 200, "msg": "success", "data": null}
```

**Response (rate limit exceeded — Quirk 15):**
```json
{"code": 403, "msg": "Data saving failed. Please try again later.", "data": null}
```

---

## All 16 Known API Quirks

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

### Quirk 13 — Legacy controllers require read-before-write (all ~138 flat fields)

Legacy controllers (`newFrameworkDevice=false`) require the full set of ~138 flat scalar
fields in every write request to `/dev/addDevMode`. Sending a partial payload results in
the omitted fields being reset to zero/default, which can turn off ports or wipe schedules.

The correct pattern is:
1. Call `getdevModeSettingList` with `devId` + `port` + auth to get the 142-field response
2. Take all 140 flat scalar fields from `data`; exclude `modeSetid` (Quirk 11), `fieldSet`
   (list), and `devSetting` (nested dict) — these cannot be form-encoded
3. Overlay the desired change
4. Send the complete merged payload (~138 fields) to `/dev/addDevMode`

Note: AI+ controllers (`newFrameworkDevice=true`) return the same 142-field structure
from `getdevModeSettingList` and benefit from the same read-before-write pattern.

---

### Quirk 14 — AI+ controllers: live write path is unknown

AI+ controllers (`newFrameworkDevice=true`, `devType=22`) use the same read-before-write
pattern and return the same 142-field structure from `getdevModeSettingList` as legacy
controllers. However, the write endpoint differs:

- `POST /dev/addDevMode` returns `{"code": 100001, "msg": "Something went wrong with your request."}` for AI+ devices — this endpoint is for legacy only.
- Phase 8 exhaustively probed 11 endpoint variants; all returned HTTP 404 except `addDevMode`.

**Current status:** AI+ `dry_run=True` is fully supported and returns the payload that
would be sent. AI+ `dry_run=False` is not yet implemented and returns a documented error.

**To discover the AI+ write endpoint:** Use mitmproxy to intercept mobile app traffic
while making a setting change on an AI+ controller. Update this quirk and implement the
branch in `client.py::set_port_mode` once discovered.

Detection:
```python
from ac_infinity_mcp.controller import ControllerType, detect_controller_type
ct = detect_controller_type(device_data)
is_ai_plus = ct == ControllerType.NEW_FRAMEWORK  # devType >= 20 or newFrameworkDevice=True
```

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

Read-only calls (`devInfoListAll`, `dataPage`, `getdevModeSettingList`) are not rate-limited.

---

### Quirk 16 — `getdevModeSettingList` requires `port` parameter; returns one dict per call

The `/dev/getdevModeSettingList` endpoint requires a `port` parameter (1-based integer).
Omitting `port` returns `{"code": 999999, "msg": "Operation failed, please try again"}`.
The response `data` field is a **single dict** for that port — not a list of all ports.

To read settings for all ports on a device, call the endpoint once per port:

```python
for port in range(1, port_count + 1):
    settings = get_mode_settings(dev_id, port)
    # settings is a dict with 142 fields for that port
```

The `externalPort` field in the response matches the `port` parameter sent.
Both legacy and AI+ controllers return the same 142-field structure.
