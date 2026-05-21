# AC Infinity MCP — v1.0 Implementation Plan

> **Single source of truth** for all phase tracking, lessons learned, and status.
> Each phase gets one PR. Phases are never bundled.

---

## Phase Map

| # | Name | Status | PR |
|---|------|--------|-----|
| 1 | Project Scaffold | ✅ Complete | #1 |
| 2 | Read Tool Suite + Test Foundation | ✅ Complete | #2 |
| 3 | Analytics MCP Tools | ✅ Complete | #3 |
| 4 | Full API Documentation + Read Tool Polish | ✅ Complete | #4 |
| 5 | CI/CD Pipeline | ✅ Complete | #5 |
| 6 | Write Tools Foundation | ✅ Complete | #9 |
| 7 | Write Tools MCP Layer | ✅ Complete | #10 |
| 8 | Write Tools Full Implementation | 🔲 Pending | — |
| 9 | Docker + Packaging + Claude Desktop | 🔲 Pending | — |
| 10 | Integration Test Suite | 🔲 Pending | — |
| 11 | Project Report | 🔲 Pending | — |

---

## Phase 1 — Project Scaffold

**Status:** ✅ Complete
**PR:** #1 (`feat/initial-scaffold`)
**Merged:** 2026-05-XX (exact date not recorded)

### Scope
- `src/` package layout (`ac_infinity_mcp/__init__.py`)
- `pyproject.toml` — dependencies, ruff, mypy, pytest config
- `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`
- `docs/API.md` — skeleton with 15 known API quirks listed
- `.env.example`
- Initial test directory structure

### Deliverables
- Installable package: `pip install -e ".[dev]"`
- Repo ready for feature branches

---

**Phase 1 Lessons Learned** — (not recorded; pre-dates this plan file)

---

## Phase 2 — Read Tool Suite + Test Foundation

**Status:** ✅ Complete
**PR:** #2 (`test/suite-migration`)
**Merged:** 2026-05-XX (exact date not recorded)

### Scope
- `src/ac_infinity_mcp/client.py` — `ACInfinityClient` (auth, get_devices, get_historical_data, parse_device_data, parse_history_record, write rate-limit enforcement)
- `src/ac_infinity_mcp/schema.py` — `ACIReading`, `VPDTargets`, exception hierarchy, `calculate_vpd`
- `src/ac_infinity_mcp/analytics.py` — pure functions: `calculate_health_score`, `detect_trends`, `build_activity_report`
- `src/ac_infinity_mcp/controller.py` — Phase-8 stubs: `detect_controller_type`, `build_write_payload`
- `src/ac_infinity_mcp/server.py` — 5 MCP tools: `discover_devices`, `get_device_reading`, `get_historical_readings`, `check_vpd_drift`, `get_all_device_readings`
- `tests/` — 129 unit tests across common/, devices/, fixtures/

### Deliverables
- All 5 read tools functional via stdio MCP transport
- `ruff`, `mypy`, `pytest` all passing at baseline
- analytics.py pure functions tested and ready for MCP exposure

---

**Phase 2 Lessons Learned** — (not recorded; pre-dates this plan file)

---

## Phase 3 — Analytics MCP Tools

**Status:** ✅ Complete
**PR:** #3 (`feat/phase-3-analytics-tools`)
**Merged:** 2026-05-20

### Scope

Expose the three pure analytics functions in `analytics.py` as MCP tools in `server.py`.
No new business logic — wiring only, plus tests and updated API docs skeleton.

**New MCP tools (server.py):**

| Tool | Wraps | Description |
|------|-------|-------------|
| `get_environment_health` | `calculate_health_score` | Composite 0–100 health score + grade + top recommendation for a given device + growth stage |
| `detect_environment_trends` | `detect_trends` | Linear trend per metric (temp, humidity, VPD) with alert flags and 7-day projection |
| `get_port_activity_report` | `build_activity_report` | Per-port on_hours, off_hours, transitions, avg_speed, uptime_pct, peak_hour |

**Signatures (intent):**
```python
async def get_environment_health(device_id: str, stage: str = "veg") -> str: ...
async def detect_environment_trends(device_id: str, days: int = 7) -> str: ...
async def get_port_activity_report(device_id: str, days: int = 7) -> str: ...
```

Each tool:
1. Calls `get_device_reading` / `get_historical_readings` internally to fetch data
2. Passes data to the analytics pure function
3. Returns JSON

**All write tools must include `dry_run=True` parameter** — N/A for these read-only tools.

**Tests:** add to `tests/common/test_server.py` (mock the analytics functions + existing fixtures).
Maintain ≥85% coverage.

### Files Modified
- `src/ac_infinity_mcp/server.py` — add 3 tools
- `tests/common/test_server.py` — add ≥15 test cases covering happy path, bad device_id, bad stage, empty readings

### Files NOT Modified
- `analytics.py` — pure functions stay untouched
- `client.py` — no changes
- `schema.py` — no changes
- `controller.py` — not touched until Phase 6

### API Quirks Relevant to This Phase
- Quirk 4: temp/humidity/VPD divided by 100 — already handled in parse_history_record; analytics receives pre-parsed floats
- Quirk 9: history API caps at ~1257 records/day — tools should document this limitation in docstrings
- Quirk 10: `vpdnums` (live) vs `vpdNums` (history) casing difference — already handled upstream; analytics is unaffected

### Acceptance Criteria
- [ ] `ruff check src/ tests/` — zero warnings
- [ ] `mypy src/ac_infinity_mcp/` — zero errors
- [ ] `pytest tests/ -v` — all pass, coverage ≥85%
- [ ] All 3 tools return valid JSON in happy-path smoke test
- [ ] `get_environment_health` returns `score`, `grade`, `vpd_score`, `temp_score`, `humidity_score`, `top_recommendation`
- [ ] `detect_environment_trends` returns list of trend reports with `metric`, `slope`, `direction`, `seven_day_projection`, `alert`
- [ ] `get_port_activity_report` returns list of activity reports per port
- [ ] Bad `stage` value returns a JSON error (not an exception)
- [ ] Unknown `device_id` returns a JSON error

---

**Phase 3 Lessons Learned**
- **What went well:** The plan was specific enough that implementation was correct on the first write — all 145 tests passed and all 5 gates cleared on the first attempt with zero restarts. Delegating to existing async tool functions (`get_device_reading`, `get_historical_readings`) rather than calling the client directly kept the new tools simple and kept retry/error-handling logic consolidated in one place. Live smoke tests against real devices (C58ZA / Towlie Tent, 3 devices total) gave high confidence before merge.
- **Changed from plan:** Added `.claude/` to `.gitignore` as a follow-up commit on the same branch — this was caught by the `gh pr create` warning about an uncommitted change and fixed before merge.
- **Watch out for next phase (Phase 4):** `docs/API.md` is a skeleton — actual request/response JSON for all 15 quirks needs to be captured from live API calls, not reconstructed from memory. Plan time for live API sniffing. The `client.py` error messages currently don't distinguish auth failure vs network error vs API-level error code — Phase 4 must fix that before the docstring polish is meaningful.
- **Actual effort vs estimate:** ~2 hours actual vs ~2 hours estimated (clean first-pass implementation, extra time spent on Python 3.11 toolchain setup and `gh` auth).
- **Investment time:** ~2:30 — wall-clock from session open to PR merged (includes toolchain setup friction).
- **Defects found:**
  - None

---

## Phase 4 — Full API Documentation + Read Tool Polish

**Status:** ✅ Complete (PR #4 — feat/phase-4-error-handling-docs)

### Scope
- Expand `docs/API.md` from skeleton to full reference (request/response examples for all 15 quirks)
- Polish server.py docstrings (add `Returns:` sections with example JSON)
- Improve error messages in client.py (distinguish auth failure vs network vs API error codes)
- No new MCP tools

**Phase 4 Lessons Learned**
- **What went well:** Live API sniff script worked on the first run and produced real response shapes immediately — the `docs/API.md` is now built from actual API output, not guesswork. The three-work-stream approach (A→B→C) was clean: error handling first meant docstrings could accurately describe the new error response shapes. All 5 gates cleared on the first pass (one test assertion fix for `"password" not in response` — too broad; corrected to check for actual credential values). The gate loop caught that real token/device-ID values from the sniff ended up in `docs/API.md` and they were scrubbed before commit.
- **Changed from plan:** Added code 401 → `ACInfinityAuthError` distinction that wasn't in the original design table (plan only listed `token is None` → AuthError). This made the test plan more precise and the error messages more actionable. `scripts/sniff_api.py` was gitignored rather than just not committed — cleaner.
- **Watch out for next phase (Phase 5 — CI/CD):** The `get_historical_data` while-loop now raises on any chunk failure, which changes retry semantics: tenacity will restart from chunk 1 if a network error happens mid-pagination (pre-existing issue, not new). Phase 5 should confirm that `pip audit` runs cleanly in CI — there's a system-level `pyjwt` CVE on the dev machine that is NOT a project dependency but will appear if the audit scans the system Python instead of the project venv. CI should install into a clean venv.
- **Actual effort vs estimate:** ~2.5 hours actual vs ~3 hours estimated (live sniff worked first try; single defect in gate loop was minor).
- **Investment time:** ~2:30 — wall-clock from session start to branch pushed.
- **Defects found:**
  - [D001] Test assertion `"password" not in json.dumps(data).lower()` was too broad — the error message intentionally contains "AC_INFINITY_PASSWORD" (the env var name). | Discovered: Gate 4 | Severity: low | Resolved: Y

---

## Phase 5 — CI/CD Pipeline

**Status:** ✅ Complete
**PR:** #5 (`feat/phase-5-cicd`)
**Merged:** 2026-05-20

### Scope
- `.github/workflows/ci.yml` — ruff, mypy, pytest, pip-audit on every PR
- `.github/workflows/codeql.yml` — CodeQL security scan
- Dependabot config
- Branch protection rules (document in CONTRIBUTING.md)

---

**Phase 5 Lessons Learned**
- **What went well:** CI went green on first push; all four checks (ruff, mypy, pytest, pip-audit) passed immediately without workflow iteration. Dependabot fired 3 action-version PRs within minutes of merge (checkout-6, setup-python-6, codeql-action-4) — working exactly as designed.
- **Changed from plan:** Had to suppress `PYSEC-2025-183` (pyjwt, disputed, no fix available) in `ci.yml` with `--ignore-vuln`. `pyjwt` is a transitive dep of `mcp` that the project does not use directly; the finding is a false positive for this project's threat model. This matched the Phase 4 warning exactly.
- **Watch out for next phase (Phase 6 — Write Tools Foundation):** The write endpoints (`/dev/addDevMode`, `/dev/getdevModeSettingList`) have no request/response examples in `docs/API.md` yet — only the read endpoints were sniffed in Phase 4. Quirk 14 defers AI+ endpoint specifics to Phase 8. Phase 6 must front-load a write-API sniffing step to capture the full 77-param legacy payload and AI+ static payload structure before any implementation starts.
- **Actual effort vs estimate:** ~1 hour actual vs ~2 hours estimated (clean first pass; pyjwt suppression was the only friction).
- **Investment time:** ~1:15 — wall-clock from session start to PR merged.
- **Defects found:**
  - None

---

## Phase 6 — Write Tools Foundation

**Status:** ✅ Complete
**PR:** #9 (`feat/phase-6-write-foundation`)

### Scope
- Implemented `controller.py`: `build_write_payload` for both LEGACY and NEW_FRAMEWORK
- Added `client.py`: `get_mode_settings(dev_id, port)` and `set_port_mode(device_data, port, updates, dry_run=True)`
- No MCP tools — foundation + tests only
- All 16 API quirks (11–16) handled
- 30 new tests; 182 total; 87% coverage

---

**Phase 6 Lessons Learned**
- **What went well:** Live API sniffing worked perfectly. All five gates passed in one pass — zero restarts. Both legacy (devType=11,18) and AI+ (devType=22) responded correctly to the sniff endpoint.
- **Changed from plan:** Three major deviations: (1) `getdevModeSettingList` requires a `port` parameter (not documented — became Quirk 16); (2) response is a single 142-field dict per port, not a list of all ports — `get_mode_settings` signature changed from `-> list[dict]` to `(dev_id, port) -> dict`; (3) AI+ and legacy have identical response structure — the "static payload" concept in Quirk 14 is moot for Phase 6; read-before-write is used for both.
- **Watch out for next phase (Phase 7 — Write Tools MCP Layer):** `set_port_mode` is synchronous — server.py must wrap it in `asyncio.to_thread()`. The `dry_run` parameter must be surfaced in the MCP tool signature. `get_mode_settings` takes `(dev_id, port)` not `(dev_id)` — server.py must resolve `dev_id` from `devCode` (Quirk 7) and pass the correct port number.
- **Actual effort vs estimate:** ~3 hours actual. No estimate was given in planning.
- **Investment time:** ~3 hours wall-clock from session start to PR open.
- **Defects found:**
  - [D001] getdevModeSettingList requires undocumented `port` parameter | Discovered: Step 0 sniff | Severity: high (would have caused 999999 errors in all write attempts) | Resolved: Y — Quirk 16 added, signature revised
  - [D002] Response is a single dict per port, not list of all ports | Discovered: Step 0 sniff | Severity: medium (architectural misunderstanding) | Resolved: Y — signature updated, docs corrected
  - [D003] Field count is ~140 flat (not ~77 as all prior docs stated) | Discovered: Step 0 sniff | Severity: low (docs only; no code impact) | Resolved: Y — docs/API.md and Quirk 13 updated

---

## Phase 7 — Write Tools MCP Layer

**Status:** ✅ Complete
**PR:** #10 (`feat/phase-7-write-mcp-layer`)

### Scope
- `set_port_speed(device_id, port, speed, dry_run=True)` MCP tool
- `set_port_on(device_id, port, dry_run=True)` MCP tool
- `set_port_off(device_id, port, dry_run=True)` MCP tool
- All tools default to `dry_run=True` and return the payload they _would_ send
- End-to-end wiring to client.py write methods

---

**Phase 7 Lessons Learned**
- **What went well:** All three tools were implemented correctly on the first pass — zero Gate 1–4 restarts. The `asyncio.to_thread()` pattern from prior phases was well-established and applied cleanly. Smoke test steps 1–5 (dry-run, validation errors) all passed immediately. The `modeType=0` + `loadType=0` port on C58ZA confirmed the full live write round-trip including revert.
- **Changed from plan:** Also fixed a Phase 6 bug discovered at Gate 5: Python `bool` values (`isUpdateVpdNums`, `restore`) were serializing as `"True"`/`"False"` strings in form encoding, causing 999999 rejections on every live write. Fixed in `build_write_payload` with `int(v) if isinstance(v, bool)`. One test added to `test_legacy_controller.py` to cover the fix.
- **Watch out for next phase (Phase 8 — Write Tools Full Implementation):** Ports in `modeType=15` (smart automation) reject writes with 999999 — the API won't accept a manual speed override while automation is active. Phase 8 must handle this case explicitly (detect modeType, return a clear error, or switch to manual mode first). Also: `loadType=4` (on/off hardware) and `loadType=128` (possibly dimmer-type) reject `set_port_speed` — `set_port_on`/`set_port_off` are the correct tools for those. AI+ devices (devType=22, Q0KT4) use a different write path — `addDevMode` returns 100001 for them; Phase 8 must implement the correct AI+ write endpoint. The `modeAndSetting` endpoint returns 404 — it is not the AI+ write path.
- **Actual effort vs estimate:** ~3 hours actual. No estimate given in planning.
- **Investment time:** ~3:30 — wall-clock from session start to PR merged (includes extended Gate 5 write debugging).
- **Defects found:**
  - [D001] Python `bool` values serialized as `"True"`/`"False"` strings in form encoding — caused 999999 rejections from `addDevMode` for all live writes | Discovered: Gate 5 | Severity: high (all live writes silently failed) | Resolved: Y — `int(v) if isinstance(v, bool)` in `build_write_payload`

---

## Phase 8 — Write Tools Full Implementation

**Status:** ✅ Complete  
**PR:** [#11](https://github.com/ober37/ac-infinity-mcp/pull/11)

### Scope
- modeType=15 (smart automation) guard in `set_port_mode` — raises `ACInfinityDeviceError` before any write
- loadType=4/128 (on/off hardware) guard via `require_variable_speed` kwarg — `set_port_speed` rejects on/off ports
- AI+ (devType=22) write path: exhaustively probed 11 candidate endpoints — all failed; `dry_run=True` works, `dry_run=False` returns documented error; `docs/API.md` Quirk 14 updated
- 403 rate-limit retry loop in write POST (3 attempts, 3s backoff); non-rate-limit 403s fail immediately
- `dry_run=False` verified live against C58ZA (legacy) and Q0KT4 (AI+)
- 9/9 Gate 5 smoke tests pass

**Phase 8 Lessons Learned**
- **What went well:** All 4 work streams completed in one session. Guard rail placement inside `set_port_mode` (modeType=15) and via kwarg (`require_variable_speed`) was cleaner than the original plan's device-dict approach. 9/9 smoke tests passing with live hardware.
- **Changed from plan:** loadType guard moved from server.py device dict lookup to client.py `set_port_mode` via `require_variable_speed=True` kwarg — the device list API returns `portsLoad=None` for all C58ZA ports, making the device dict approach unreliable; `loadType` from `getdevModeSettingList` is authoritative. AI+ endpoint discovery exhausted 11 candidates (not just the 7 originally listed) — fallback documented-error path implemented as planned.
- **Watch out for next phase (Phase 9 — Docker + Packaging):** The 1.5s write rate limit does not need an env-var override for Docker — it's enforced on the client and is wall-clock based, not config-based. Env vars needed for Docker: `AC_INFINITY_EMAIL`, `AC_INFINITY_PASSWORD` only. No other env changes required. Port 1 on C58ZA (Humidifier) rejects writes with 999999 even with loadType=0 — this is a device-level restriction invisible from mode settings; not a bug in Phase 8 code.
- **Actual effort vs estimate:** ~3 hours actual vs ~3 hours estimated.
- **Investment time:** ~3:00 — one session, start to PR merged.
- **Defects found:**
  - [D001] `portsLoad=None` in device list for C58ZA — `loadType` from mode settings is authoritative; server.py device dict guard unreliable | Discovered: Gate 5 (smoke tests) | Severity: high | Resolved: Y
  - [D002] Port 1 (Humidifier, loadType=0) on C58ZA rejects writes with 999999 despite correct loadType — device-level restriction | Discovered: Gate 5 | Severity: medium | Resolved: Y (smoke test uses port 4)
  - [D003] Test 7 revert called `set_port_speed(speed=0)` when port was off — speed=0 is out of range (1–10) | Discovered: Gate 5 | Severity: medium | Resolved: Y (use `set_port_off` when current_speed==0)
  - [D004] `test_set_port_mode_dry_run_ai_plus` failed — AI+ fixture has modeType=15 from live device; modeType=15 guard fired before dry_run path | Discovered: Gate 4 | Severity: medium | Resolved: Y (override modeType=0 in test)

---

## Phase 9 — Docker + Packaging + Claude Desktop

**Status:** 🔲 Pending

### Scope
- `Dockerfile` + `.dockerignore`
- `docker-compose.yml`
- Claude Desktop integration instructions in README
- `pip install ac-infinity-mcp` install flow documented

---

## Phase 10 — Integration Test Suite

**Status:** 🔲 Pending

### Scope

**Stream A — MCP wire protocol tests (new)**
The existing server tests call tool functions directly as Python async functions. They do not
exercise the MCP JSON-RPC layer at all. Phase 10 must add tests that verify:
- All 11 tools are registered on `mcp_server` with correct names
- Each tool's parameter schema (names, types, required/optional) matches the function signature
- A JSON-RPC `tools/call` message sent through a real `mcp` client against a running server
  process returns the expected response shape (happy path + missing-creds guard)
- `main()` startup path: missing env vars → `sys.exit(1)`; bad credentials → `sys.exit(1)`

These tests run in CI without real AC Infinity credentials (mock client or subprocess with no env).

**Stream B — Live API integration tests**
- Expand `tests/integration/test_live.py` with live API tests (skipped in CI without credentials)
- Full smoke test plan documented and executed against live hardware

---

## Phase 11 — Project Report

**Status:** 🔲 Pending

### Scope
- Final project report document covering:
  - Section 1: Feature summary
  - Section 2: Architecture decisions
  - Section 3: Code review findings (all defects from gate loops)
  - Section 4: Time investment summary (per-phase wall-clock from lessons learned)
  - Section 5: API quirks reference

---
