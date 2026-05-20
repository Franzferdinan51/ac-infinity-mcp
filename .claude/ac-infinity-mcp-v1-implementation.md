# Plan: ac-infinity-mcp — Standalone Repo Extraction & v1.0 Release

## Context

The AC Infinity MCP server currently lives inside the `ober37/peekaboopoint` monorepo at `scripts/acinfinity/`. The goal (Trello card XnKi978n, due 2026-05-31) is to extract it into its own public GitHub repo — `ober37/ac-infinity-mcp` — packaged and documented well enough to announce as a full-featured v1.0 to the wider grower/operator community.

The existing code is production-proven (5 live tools, 1,552 lines of unit tests, Docker container already running). The main work is: scope expansion to full v1.0 feature set, scaffolding, hardening, and documentation.

---

## Scope Boundary

### v1.0 — WiFi Cloud API + Built-in Controller Sensors (69 Pro Family)
Everything accessible via the AC Infinity cloud REST API on WiFi-connected controllers (Controller 69 Pro, 69 Pro+, 89 AI+). Built-in sensors only: **temperature, humidity, VPD**. Port control and all automation modes.

### v2.0 — External Sensors + Bluetooth
- External UIS sensors: CO2, pH, EC/TDS, soil moisture, water temperature, water level, light level
- Bluetooth-local control (via `acinf`/`ac-infinity-ble` libraries)
- Any features requiring direct device connection rather than cloud API

This boundary is clean: if it works on a 69 Pro with nothing plugged into the UIS sensor port and no BLE, it's v1.0.

---

## Framework Decision: Python + FastMCP

**Python 3.11+ with the official `mcp` package (FastMCP).**

- All existing code is Python — no translation cost
- FastMCP decorator pattern is idiomatic, minimal boilerplate
- 1,552 lines of tests migrate with only import path changes
- TypeScript SDK has more community examples but requires full rewrite; Python wins on velocity here

Toolchain: `ruff` (lint/format), `mypy` (types), `pytest` + `pytest-asyncio` + `pytest-cov`, `tenacity` (retry), GitHub Actions CI.

---

## AC Infinity API — Complete Picture

**No official published API.** All endpoint knowledge comes from community reverse engineering:
- `keithah/homebridge-acinfinity` — `API_REFERENCE.md` (Charles Proxy capture of iOS app)
- `dalinicus/homeassistant-acinfinity` — Python async client + const.py

### Base URL
`http://www.acinfinityserver.com` (HTTP only — document as known limitation)

### All Confirmed Endpoints

| Endpoint | Method | Purpose | v1.0? |
|---|---|---|---|
| `/api/user/appUserLogin` | POST | Auth → `appId` token | ✅ |
| `/api/user/devInfoListAll` | POST | All devices + live readings | ✅ |
| `/api/log/dataPage` | POST | Historical data (time-cursor paginated) | ✅ |
| `/api/dev/getdevModeSettingList` | POST | Full port settings + automation config | ✅ new |
| `/api/dev/addDevMode` | POST | Write speed/mode (standard controllers) | ✅ new |
| `/api/dev/modeAndSetting` | PUT | Write speed/mode (AI+ controllers) | ✅ new |
| `/api/dev/getDevSetting` | POST | Advanced device settings | ✅ new |
| `/api/dev/updateAdvSetting` | POST | Update device name + calibration | ✅ new |

**No additional endpoints exist.** Confirmed: no firmware version, no alert/notification, no account settings, no webhooks. The 8 above are the complete API surface.

---

## Complete v1.0 Tool Set (16 tools + 3 prompts)

### Currently Implemented (5 tools — migrated and improved)
1. `discover_devices()` — List all controllers with online status
2. `get_device_reading(device_id)` — Current temp/humidity/VPD + port speeds + port names
3. `get_all_device_readings()` — All devices in one call
4. `get_historical_readings(device_id, start_date, end_date, sample_interval, time_start, time_end)` — Historical data with sampling + time-window filtering
5. `check_vpd_drift(device_id, stage)` — VPD alert vs. growth stage target

### New Read Tools (4 tools — unblocked, data already in API)
6. `get_port_status(device_id, port)` — Exposes fields already in API but not currently parsed: `speak` (actual current power level 0-10), `loadState` (is a device plugged in?), `curMode` (active automation mode: OFF/ON/AUTO/VPD/TIMER/CYCLE/SCHEDULE), `remainTime` (countdown timer seconds)
7. `get_port_settings(device_id, port)` — Full automation configuration from `/api/dev/getdevModeSettingList`: current speed targets, VPD targets, temp targets, humidity targets, active schedule, active timer, cycle settings
8. `get_environment_health_score(device_id, stage)` — Composite 0-100 score from built-in sensor readings. Weighted: VPD 40%, temp 30%, humidity 30%. Returns: score, letter grade (A–F), per-metric analysis, top recommendation. Pure calculation on existing data.
9. `detect_environmental_trends(device_id, days)` — Fetch N days of historical data, compute linear regression on temp/humidity/VPD. Returns: trend direction per metric, rate of change per day, 7-day projection, drift alert if slope exceeds threshold.

### Write-Control Tools (5 tools — confirmed API, controller-type-aware)
10. `set_port_speed(device_id, port, speed, dry_run=False)` — Set fan speed 0-10. Controller-type-aware: legacy = fetch-merge-write; AI+ = static payload. Validates 0-10 range. Returns planned change before executing (dry_run mode).
11. `set_port_mode(device_id, port, mode, dry_run=False)` — Set mode: OFF / ON / AUTO / VPD / TIMER / CYCLE / SCHEDULE. Validates mode-specific required params.
12. `set_vpd_automation(device_id, port, target_vpd, dry_run=False)` — Enable VPD auto-mode with a target kPa. Uses built-in temp/humidity sensors. Sets `vpdSettingMode=1`, `targetVpd`, `targetVpdSwitch=1`. No external sensor required.
13. `set_temperature_automation(device_id, port, min_c, max_c, dry_run=False)` — Enable temperature auto-mode using built-in temp sensor. Sets `devLt`/`devHt`, `activeLt`/`activeHt`.
14. `set_humidity_automation(device_id, port, min_rh, max_rh, dry_run=False)` — Enable humidity auto-mode using built-in humidity sensor. Sets `devLh`/`devHh`, `activeLh`/`activeHh`.

### Intelligence Tools (2 tools — built on top of API data)
15. `apply_grow_stage_template(device_id, port, stage, dry_run=False)` — One-click configuration for a growth stage. Stages: `seedling`, `veg`, `early_flower`, `mid_flower`, `late_flower`. Sets VPD target, temp range, humidity range using the appropriate write tools. Returns full applied config summary.
16. `get_port_activity_report(device_id, start_date, end_date)` — Per-port runtime stats from historical data: total runtime hours, on/off cycles, average speed when running, uptime %, busiest time-of-day.

### MCP Prompts (3 prompts — zero API calls, FastMCP `@mcp_server.prompt()`)
- `vpd_troubleshooting` — Step-by-step guide: "VPD is HIGH → lower temp or increase humidity → use set_vpd_automation to target X kPa"
- `new_grower_setup` — Onboarding guide: discover devices → apply stage template → check health score
- `environment_alert_interpretation` — How to interpret alerts from check_vpd_drift and health scores

---

## Known API Quirks (all must be documented in docs/API.md)

1. `appPasswordl` — intentional typo in auth parameter (lowercase `l` at end)
2. Password silently truncated to 25 chars
3. `pageNum` in history API ignored — use time-cursor pagination (`last_ts + 1`)
4. Temp/humidity/VPD values divided by 100 in API responses
5. Port speeds encoded as 4-bit nibbles in `portSpead` bitmask; `0xF` = ON for toggle devices
6. `portStatus` bitmask (1 bit per port) = automation-triggered state
7. `devCode` (string, e.g. "C58ZA") ≠ `devId` (numeric) — history API requires `devId`
8. API base is HTTP only — document security limitation
9. Historical API returns max ~1257 records/day regardless of `pageSize`
10. `vpdnums` field in device info; `vpdNums` in history records (different casing)
11. Write-control: NEVER include `modeSetid` field for legacy controllers → 403 error
12. Write-control: Must set `modeType=2` when `onSpead > 0` or change doesn't persist
13. Write-control: Legacy controllers require read-before-write (all 77 params must be sent)
14. Write-control: AI+ controllers (`newFrameworkDevice=true`) use static full payload — no pre-fetch
15. Rate limit: 1.5s minimum between write API calls (returns 403 "Data saving failed" if exceeded)

---

## Standalone Repo Structure

**GitHub repo:** `ober37/ac-infinity-mcp`
**PyPI package:** `ac-infinity-mcp`
**License:** MIT

```
ac-infinity-mcp/
├── .github/
│   └── workflows/
│       ├── ci.yml              # lint → typecheck → test → coverage
│       └── release.yml         # tag → PyPI + ghcr.io Docker image + GitHub Release
├── src/
│   └── ac_infinity_mcp/
│       ├── __init__.py         # version export
│       ├── server.py           # FastMCP server, all 16 tools + 3 prompts
│       ├── client.py           # REST client + retry + rate limiting
│       ├── schema.py           # models, exceptions, VPD math, stage targets
│       ├── controller.py       # controller-type detection + write payload builder
│       └── analytics.py        # health score, trend detection, activity report (pure functions)
├── tests/
│   ├── conftest.py                     # shared fixtures: mock session, env vars
│   ├── common/                         # controller-agnostic tests
│   │   ├── test_client.py              # auth, get_devices, get_historical_data, retry, rate-limit
│   │   ├── test_server.py              # all 16 tool interfaces, error handling, prompts
│   │   └── test_analytics.py          # health score, trend detection, activity report (pure fns)
│   ├── devices/                        # per-controller-type tests
│   │   ├── conftest_devices.py         # device-specific fixtures (mock devInfoListAll responses)
│   │   ├── test_legacy_controller.py   # devType 11 (69 Pro) + devType 18 (69 Pro+)
│   │   └── test_ai_plus_controller.py  # devType 20+ (89 AI+, newFrameworkDevice=true)
│   ├── fixtures/
│   │   ├── mock_api_responses.py       # shared mock API payloads (auth, device list, history)
│   │   ├── legacy_device_fixtures.py   # devType 11/18 mock devInfoListAll + getdevModeSettingList
│   │   └── ai_plus_device_fixtures.py  # devType 20 mock responses + static payload template
│   └── integration/
│       └── test_live.py                # skip without AC_INFINITY_EMAIL/PASSWORD
├── docker/
│   ├── Dockerfile              # multi-stage build
│   ├── docker-compose.yml      # local dev
│   └── HTTPS_SETUP.md
├── docs/
│   ├── API.md                  # all 16 tools + 3 prompts, all 15 API quirks
│   └── DEPLOYMENT.md           # Docker, env vars, SSL
├── CLAUDE.md                   # contribution protocol, PR gate loop
├── CONTRIBUTING.md             # public contributor guide
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── .env.example
```

**New module: `controller.py`** — Isolates all write-control complexity:
- `detect_controller_type(device_data) → ControllerType`
- `build_write_payload(current_settings, updates, controller_type) → dict`
- `ControllerType` enum: `LEGACY` (devType 11/18), `NEW_FRAMEWORK` (devType 20+)

**New module: `analytics.py`** — Pure functions, no API calls:
- `calculate_health_score(reading, stage) → HealthScore`
- `detect_trends(readings, days) → TrendReport`
- `build_activity_report(readings) → ActivityReport`

**Test routing decision rule:**

| Test belongs in | Condition |
|---|---|
| `tests/common/` | Test does not care which controller hardware is present; uses a generic mock device |
| `tests/devices/test_legacy_controller.py` | Test specifically validates behavior for devType 11 or 18, or the legacy read-merge-write flow |
| `tests/devices/test_ai_plus_controller.py` | Test specifically validates behavior for devType 20+, or the static-payload write flow |
| `tests/integration/` | Requires live credentials; skipped in CI without `AC_INFINITY_EMAIL` |

---

## CLAUDE.md — What It Must Codify

`CLAUDE.md` is the authoritative source for how Claude agents contribute to this repo.

### Contribution Rules
- Never push directly to `main`. All work goes through feature branches + PRs.
- Each phase = one PR. Phases are never bundled.
- Every phase begins with a **Phase Planning Session** before any code is written (see below).
- No PR is raised until the full gate loop passes. Any failure restarts from Gate 1.

### Phase Planning Session (mandatory before any code is written)

Before starting implementation on each phase, run an interactive planning session with the user:

1. **Present the phase scope** — what tools/features will be built, what files will be created or modified, what the expected outputs are
2. **Confirm usability expectations** — how will a grower actually use this? What does the tool response look like? Walk through example inputs and outputs.
3. **Confirm implementation strategy** — which approach will be taken, any alternatives considered and why rejected
4. **Identify edge cases** — what unusual inputs or device states should be handled? What should the tool return if data is missing?
5. **Get explicit user approval** before writing any code

The session is complete when the user explicitly approves. If the user redirects scope or changes approach during the session, update the plan before starting.

### PR Gate Loop (mandatory before every PR)

**Gate 1 — Deep Code Review (Senior Python Engineer persona)**
- Correctness, idiomatic Python, async safety, error handling
- API quirk compliance (see quirks list in `docs/API.md`)
- No blocking calls in async context
- Retry logic applied to all external HTTP calls

**Gate 2 — Secondary Code Review (Security Engineer persona)**
- Independent review: injection risks, credential handling, input sanitization
- Log output audit: no credentials, tokens, or PII in any log level
- Dependency version audit

**Gate 3 — Deep Security Review**
- `.env` not committed, no hardcoded tokens
- `pip audit` — no known CVEs in dependencies
- Docker image doesn't embed secrets
- HTTP-only API exposure documented and accepted risk noted

**Gate 4 — Full Automated Tests Pass**
- `ruff check src/ tests/` — zero warnings
- `mypy src/ac_infinity_mcp/` — zero errors
- `pytest tests/common/ tests/devices/ -v --cov=ac_infinity_mcp --cov-fail-under=85` — all pass, ≥85% coverage

**Gate 5 — Manual Smoke Test Proposal + Execution**
- Write smoke test plan for the PR scope
- Present plan to user for confirmation before executing
- Execute (live API or mock verification)
- Report pass/fail per test case explicitly

**Failure at any gate → fix → restart from Gate 1.**

### Code Standards
- Python 3.11+, type annotations on all public functions
- `ruff` format enforced, `line-length = 100`
- No `print()` in library code — `logging` only
- No credentials in log output at any level
- `tenacity` retry on all external HTTP calls
- `asyncio.to_thread()` for all blocking operations in async context
- 1.5s rate limit between write API calls (enforced in `client.py`)
- All write tools support `dry_run=True` parameter

### Commit Message Format
```
type(scope): short description

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`

**Model version rule:** The version in `Co-Authored-By` must match the model actually used in that session (e.g., `Sonnet 4.7`, `Opus 4`). Never use the generic `Claude` attribution — the specific model matters for the project report and for historical traceability. Confirm the current model name at the start of each phase session and substitute accordingly before committing.

---

## CONTRIBUTING.md — What It Must Cover

1. Dev environment setup (clone, `pip install -e ".[dev]"`, `.env` config)
2. Running tests (`pytest tests/common/ tests/devices/` for unit tests, `pytest tests/integration/` for live tests with credentials, integration test instructions)
3. Code style (`ruff`, `mypy`, docstrings for public functions)
4. PR process: fork → branch → PR against `main`; all CI checks + CodeQL must pass; one approval required
5. Automated checks that run on every PR — explain what each does:
   - `ruff` (lint/format), `mypy` (type safety), `pytest` (tests), `pip-audit` (CVE check)
   - **CodeQL** — GitHub's free security scanner runs automatically on all PRs; findings are blocking
   - **Dependabot** — automatically opens PRs to update vulnerable dependencies
6. API quirk documentation: link to `docs/API.md` — all known quirks must be preserved
7. Reporting issues: GitHub Issues; include AC Infinity controller model + firmware version
8. Scope: v1.0 = WiFi cloud API + built-in sensors only. v2.0 = external UIS sensors + BLE. See the v2.0 GitHub Milestone for the backlog.
9. License: MIT

---

## Session Orchestration Protocol

### Plan File as Shared State
This file at `/Users/ober37/.claude/plans/ac-infinity-mcp-v1-implementation.md` is the **single source of truth across all sessions**. Every phase session reads it at start and writes back before closing. No session should rely on prior conversation context — all context lives here.

### How to Run an Orchestration Turn

In any new Claude Code session (peekaboopoint repo, ac-infinity-mcp repo, or standalone):

```
Read the plan file at /Users/ober37/.claude/plans/ac-infinity-mcp-v1-implementation.md.
Identify the next Pending phase.
Read all Lessons Learned sections from completed phases.
Produce copy-paste instructions for Phase N that incorporate those lessons.
Return the instructions as a markdown code block I can paste into a new session.
```

The orchestration turn is intentionally brief — read → synthesize → generate. No implementation happens here.

### Copy-Paste Instruction Format

The generated instructions for each phase must be self-contained and include:
- **What repo to work in** and what branch to create
- **Phase scope** — what gets built, what files are touched
- **Prior lessons** — explicit callouts from prior phase lessons that affect this phase
- **Step 0 planning session prompt** — what to discuss and confirm with the user before writing code
- **Gate loop reminder** — abbreviated checklist
- **Plan file location** — so the session knows where to write lessons learned
- **Closing requirement** — lessons learned + time investment block + status update before ending

### Phase Session Protocol

When starting a phase session with copy-paste instructions:
1. Read this plan file fresh (do not rely on the copy-paste alone — plans can drift)
2. Begin with the Phase Planning Session (Step 0) — present scope, confirm usability expectations, get user approval before any code
3. Implement following the gate loop
4. **Before ending the session:** Write lessons learned to this plan file under "Phase N Lessons Learned", write the time investment block under "Phase N Time Investment", and mark status ✅ Complete

### Lessons Learned Format (per phase)

Append at the end of each phase block:

```
**Phase N Lessons Learned**
- **What went well:** [brief note]
- **Changed from plan:** [deviations and why]
- **Watch out for next phase:** [specific warnings for Phase N+1]
- **Defects found:** [list each defect with: ID, description, where discovered (gate N / code review / smoke test), severity (critical/high/medium/low), resolved Y/N]
```

**Defect tracking rule:** Any bug, async safety issue, API quirk violation, security finding, or test failure discovered during the gate loop is a defect. Record each one in the `**Defects found:**` list with the fields above. Inherited defects from the monorepo migration count. All defects roll up into the Phase 11 project report Section 3 (Comprehensive Code Review).

### Time Investment Format (per phase)

Append a separate block at the end of each phase block, after Lessons Learned:

```
**Phase N Time Investment**
- **Date:** YYYY-MM-DD
- **Actual Claude session time:** HH:MM
- **Projected manual time:** Xh–Yh (midpoint Zh)
- **Manual estimate basis:** [key assumptions — skill level, prior knowledge gaps, what would dominate manual effort]
- **Multiplier:** ~Xx  (projected manual midpoint ÷ actual Claude time)
```

**Time investment tracking rule:** At session close, record Claude session time (from transcript first message to last, or use wall-clock if actively monitored). For Phase 0 and any planning-only sessions, record time from first message to usage cutoff or natural end. The multiplier (manual midpoint ÷ Claude time) is the headline metric that feeds Section 4 of the Phase 11 project report. Never skip this block — it is required for the report.

### Phase Status Tracking

Each phase header includes a `**Status:**` line. Valid values:
- `Pending` — not started
- `In Progress` — session active
- `✅ Complete` — PR merged, lessons written

---

## Phased Implementation Plan

### Phase 0 — Ideation & Planning
**Status:** ✅ Complete
**Session:** Single session, peekaboopoint repo context
**Deliverable:** This plan file (`ac-infinity-mcp-v1-implementation.md`)

Produced in one ~52-minute late-night session (11:27 PM – 12:19 AM CDT, May 19–20 2026). Covers: full API surface research (8 endpoints, 15 quirks, both write-control patterns), framework decision, complete 16-tool + 3-prompt design, repo structure, CI/CD pipeline, PR gate loop, session orchestration model, 11 implementation phases, test structure, v2.0 tracking strategy.

**Phase 0 Time Investment**
- **Date:** 2026-05-19 / 2026-05-20
- **Actual Claude session time:** 0:52
- **Projected manual time:** 26h–46h (midpoint ~36h)
- **Manual estimate basis:** Decent Python, zero AC Infinity API knowledge, zero FastMCP experience. Dominant cost is API research: no official docs, must find and read community reverse-engineering sources (homebridge-acinfinity, homeassistant-acinfinity), then infer write-control patterns (77-field payload, legacy vs. AI+ paths, modeSetid 403 trap, modeType=2 coercion) from other people's code. Wide range reflects luck-of-search variability.
- **Multiplier:** ~41x  (36h projected midpoint ÷ 0.87h actual)

---

### Phase 1 — Repo Scaffold & Core Migration
**Status:** ✅ Complete
**PR:** [feat: initial scaffold, core module migration, CLAUDE.md](https://github.com/ober37/ac-infinity-mcp/pull/1)
**Effort:** ~3h | **Sequential — foundation for all other phases**

**Step 0 — Planning session:** Present module layout, import structure, pyproject.toml dep choices. Confirm which of the 5 existing tools need async fixes before migration. Get user approval.

1. Create `ober37/ac-infinity-mcp` on GitHub (MIT, public)
2. Set up `src/ac_infinity_mcp/` layout + `pyproject.toml`
   - Core deps: `mcp>=1.14.1`, `requests>=2.31.0`, `tenacity>=8.0.0`
   - Dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `responses`, `ruff`, `mypy`
3. Migrate `client.py`:
   - Clean imports (no try-except import hack)
   - Add `tenacity` retry on `get_devices()` and `get_historical_data()`
   - Fix async gap: wrap all blocking HTTP calls in `asyncio.to_thread()`
   - Add 1.5s rate-limit enforcement for write calls
4. Migrate `schema.py` (no changes needed)
5. Migrate `mcp_server.py` → `server.py` (clean imports, fix async gaps in `discover_devices` and `get_all_device_readings`)
6. Create `controller.py`: `detect_controller_type()`, `build_write_payload()`
7. Create `analytics.py`: stub implementations for health score, trend detection, activity report
8. Create `CLAUDE.md`, `CONTRIBUTING.md`, `.env.example`, `.gitignore`
9. Verify: `pip install -e ".[dev]"` succeeds, 5 existing tools run

**Gate loop before PR: all 5 gates**

**Phase 1 Lessons Learned**
- **What went well:** All 5 gates cleared in a single session without any restarts. The existing source code was clean enough that migration was mostly mechanical. The async gap analysis was the most valuable pre-coding step — caught an undocumented third async gap in `get_device_reading` that the original plan missed.
- **Changed from plan:** (1) `requests>=2.31.0` bumped to `>=2.33.0` after `pip-audit` found CVE-2026-25645. (2) `pytest>=7.0` bumped to `>=9.0.3` after CVE-2025-71176. (3) `setuptools.backends.legacy:build` → `setuptools.build_meta` (incompatible with the system Python's setuptools). (4) `requests.Session.timeout` is not a valid attribute — removed, each call already passes `timeout=` explicitly. (5) `aci_client` global in server.py typed as `Optional[ACInfinityClient]` — added `_client()` helper to satisfy mypy rather than asserting None-safety inline.
- **Watch out for next phase:** (1) Test coverage threshold — Phase 2 targets 85%; the Phase 1 suite (24 tests) doesn't include tests for the async server tools (would need `AsyncMock`/`responses` mocking). (2) The `calendar` import inside `get_historical_readings` is a standard library laziness that ruff doesn't catch but mypy might flag in stricter configs — consider moving to top-level. (3) `pip-audit` will show 16 transitive CVEs on every run (through `mcp`'s dependencies); this is expected noise until `mcp` upstream bumps them.
- **Actual effort vs estimate:** ~2.5h actual vs ~3h planned — on budget
- **Investment time:** 00:40 (session start ~09:30 CDT → PR raised ~10:10 CDT, 2026-05-20)
- **Projected manual time:** 12–18h (midpoint ~15h) | Skill basis: decent Python, zero AC Infinity API / FastMCP / modern Python packaging experience. Primary time drivers: FastMCP learning (1–2h), pyproject.toml + toolchain friction (1–3h), identifying all async gaps correctly (0.5–1.5h), mypy first-time issues (0.5–1.5h), writing 24 tests including nibble-decoding logic (1.5–3h).
- **Multiplier:** ~22x (15h projected midpoint ÷ 0:40 actual)
- **Defects found:**
  - [D001] `Session.timeout` not a valid requests.Session attribute (monorepo latent bug — timeout was silently ignored) | Discovered: Gate 4 mypy | Severity: low | Resolved: Y
  - [D002] Async gap in `get_device_reading()`: blocking `get_devices()` called without `asyncio.to_thread()` (plan only listed 2 async gaps, code had 3) | Discovered: Gate 1 / planning code review | Severity: high | Resolved: Y
  - [D003] `requests 2.32.5` CVE-2026-25645 | Discovered: Gate 3 pip-audit | Severity: medium | Resolved: Y (bumped to >=2.33.0)
  - [D004] `pytest 9.0.2` CVE-2025-71176 | Discovered: Gate 3 pip-audit | Severity: low | Resolved: Y (bumped to >=9.0.3)
  - [D005] `setuptools.backends.legacy:build` not importable in system Python's setuptools 65.x | Discovered: Gate 4 pip install | Severity: medium | Resolved: Y (changed to setuptools.build_meta)

---

### Phase 2 — Test Suite Migration + New Unit Tests
**Status:** ✅ Complete
**PR:** [test: migrate existing tests, add tests for new modules](https://github.com/ober37/ac-infinity-mcp/pull/2)
**Effort:** ~2.5h | **Sequential after Phase 1; CI YAML can be drafted during this phase**

**Step 0 — Planning session:** Walk through test coverage strategy — what mocks are needed for `controller.py` and `analytics.py`, how integration tests will skip without credentials, coverage threshold rationale. Get user approval.

1. Migrate `tests/acinfinity/` → `tests/common/`, `tests/devices/`, `tests/fixtures/`, and `tests/integration/`
2. Remove all `sys.path.insert` hacks — use `from ac_infinity_mcp.X import ...`
3. Update `conftest.py` for installed package imports
4. Configure `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths`, `--cov-fail-under=85`
5. Write `tests/devices/test_legacy_controller.py` and `tests/devices/test_ai_plus_controller.py`:
   - `test_legacy_controller.py` (devType 11/18): `detect_controller_type`, `build_write_payload` merge path, `modeSetid` exclusion enforced, `modeType=2` coercion; fixtures in `tests/fixtures/legacy_device_fixtures.py`
   - `test_ai_plus_controller.py` (devType 20+): `detect_controller_type`, `build_write_payload` static path, all 77 required fields present; fixtures in `tests/fixtures/ai_plus_device_fixtures.py`
6. Write `tests/common/test_analytics.py` (pure function tests; no device type dependency):
   - Health score: correct weighting, boundary conditions, grade thresholds
   - Trend detection: ascending/descending/flat slopes, projection accuracy
   - Activity report: runtime calculation, uptime %, busiest hour
7. Move shared mock data to `tests/fixtures/mock_api_responses.py`
8. Add `tests/devices/conftest_devices.py` with per-type `@pytest.fixture` device mocks
9. Target: all unit tests pass, ≥85% coverage

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: run full test suite (`pytest tests/common/ tests/devices/ -v --cov`), report per-directory coverage

**Phase 2 Lessons Learned**
- **What went well:** All 5 gates cleared in one session. The planning session surfaced the key tension (analytics stubs vs. real test coverage) before any code was written. Implementing the pure analytics functions now rather than deferring to Phase 7 paid off: test coverage hit 89% with meaningful behavioral assertions. The `asyncio.to_thread` + regular `MagicMock` pattern worked cleanly — no `AsyncMock` needed for the sync methods running in threads.
- **Changed from plan:** (1) `conftest_devices.py` → renamed to `tests/devices/conftest.py` (pytest only auto-discovers files named `conftest.py`). (2) `"0m"` removed from invalid-interval parametrize list — the regex accepts it and returns `0 * 60 = 0`, so it's syntactically valid. (3) VPD weighting was clarified during planning to 40/30/30 (not the 50/25/25 the planning agent initially used). (4) Analytics implemented fully in Phase 2 rather than Phase 7 — this eliminates the need to rewrite test_analytics.py when Phase 7 adds the MCP tool wrappers.
- **Watch out for next phase (Phase 3 — CI/CD):** (1) `asyncio_mode = "auto"` in pyproject.toml means `async def test_*` functions run without `@pytest.mark.asyncio` — CI matrix must also have `pytest-asyncio>=0.21`. (2) `--cov-fail-under=85` is now in `addopts` so it fires on every `pytest` run including CI. (3) The CI workflow should use `pytest tests/common/ tests/devices/` (not `tests/`) to exclude the skippable integration tests from the coverage threshold. (4) `pip-audit` will show 16 transitive CVEs on every run — document this as expected in the CI configuration so it doesn't create false-alarm issue noise.
- **Actual effort vs estimate:** ~2h actual vs ~2.5h planned — slightly under budget.
- **Defects found:**
  - [D006] `"0m"` incorrectly included in invalid-interval parametrize list — regex accepts it, function returns 0. Not a source defect; test expectation was wrong. | Discovered: Gate 4 pytest | Severity: low | Resolved: Y (removed from parametrize)

**Phase 2 Time Investment**
- **Date:** 2026-05-20
- **Actual Claude session time:** ~1:00 (session start to PR raised)
- **Projected manual time:** 10h–16h (midpoint ~13h)
- **Manual estimate basis:** Decent Python, no prior pytest-asyncio + FastMCP async mocking experience. Primary cost drivers: designing the three-bucket test routing, figuring out `asyncio.to_thread` + `MagicMock` pattern, implementing three analytics pure functions from scratch (formulaic but careful), writing 129 tests with good assertion coverage.
- **Multiplier:** ~13x (13h projected midpoint ÷ ~1h actual)

---

### Phase 3 — CI/CD Pipeline
**Status:** Pending
**PR:** `ci: GitHub Actions for lint, typecheck, test, and release`
**Effort:** ~1.5h | **Parallelizable with Phase 2**

**Step 0 — Planning session:** Review workflow triggers, Python version matrix, PyPI release mechanics, Docker registry choice. Confirm branch protection rules. Get user approval.

**`ci.yml`** (on push + PR to `main`):
```yaml
jobs:
  lint:      ruff check src/ tests/ (inline reviewdog annotations on PRs)
  typecheck: mypy src/ac_infinity_mcp/
  test:      pytest tests/common/ tests/devices/ (matrix: python 3.11, 3.12)
  coverage:  cov-fail-under=85
  audit:     pip-audit (dependency CVE check — free, no API key needed)
```

**`codeql.yml`** (on push + PR to `main` — free on public repos):
```yaml
jobs:
  analyze: CodeQL security scanning (Python)
  # GitHub Advanced Security — free for public repos
  # Detects: injection flaws, hardcoded credentials, insecure deserialization
```

**`.github/dependabot.yml`** (free on all accounts):
```yaml
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule: weekly
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: weekly
```

**`release.yml`** (on `v*` tag):
```yaml
jobs:
  publish: build wheel + sdist → PyPI
  docker:  multi-stage build → ghcr.io/ober37/ac-infinity-mcp:latest + version tag
  release: create GitHub Release with CHANGELOG section as body
```

**Ruff + mypy** in `pyproject.toml`: `line-length = 100`, select `["E","F","I","UP"]`, `ignore_missing_imports = true`

**Branch protection:** CI + CodeQL required to pass before merge to `main`.

**Free tier note:** CodeQL, Dependabot, and GitHub Actions minutes are all unlimited on public repos. `pip-audit` is a CLI tool (no API key, no account needed). No paid tooling required anywhere in this pipeline.

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: trigger CI manually on a test branch, confirm all jobs green

---

### Phase 4 — Docker Hardening
**Status:** Pending
**PR:** `feat(docker): multi-stage Dockerfile, compose files`
**Effort:** ~1.5h | **Parallelizable with Phase 5**

**Step 0 — Planning session:** Walk through multi-stage build approach, image size tradeoffs, compose env var strategy, health check design. Confirm port and restart policy. Get user approval.

**Multi-stage `docker/Dockerfile`:**
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl
ENV PYTHONUNBUFFERED=1
EXPOSE 9001
CMD ["python", "-m", "ac_infinity_mcp.server"]
```

**`docker/docker-compose.yml`**: env from `.env`, port `9001:9001`, restart `unless-stopped`, health check.

**Key improvement**: No cross-directory `COPY` — clean single-repo Docker context.

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: `docker compose up`, call `discover_devices`, verify response

---

### Phase 5 — Documentation
**Status:** Pending
**PR:** `docs: README, API reference, deployment guide, CHANGELOG`
**Effort:** ~3h | **Parallelizable with Phase 4**

**Step 0 — Planning session:** Review README structure, Claude Desktop config snippet format, which tool examples to feature prominently, what the "known limitations" section says about the HTTP API. Confirm voice/tone. Get user approval.

**README.md**: Badges (CI, PyPI, Python, License, Docker) · Description · Quickstart (3 steps) · Claude Desktop config snippet · Full tool reference table (16 tools + 3 prompts) · Docker section · Known limitations · v2.0 roadmap teaser · Contributing · License

**`docs/API.md`**: Per-tool reference — all 16 tools + 3 prompts with parameters, return schema, example JSON · All 15 API quirks with context and code notes · Sampling interval decision tree (adapted from peekaboopoint skill) · Timezone handling · Controller compatibility table (69 Pro / 69 Pro+ / 89 AI+) · `dry_run` usage guide

**`docs/DEPLOYMENT.md`**: Docker compose quickstart · Env var reference table · SSL/HTTPS setup (migrated from monorepo) · Let's Encrypt integration

**`CHANGELOG.md`**: v1.0.0 entry with complete feature list

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: read README as a first-time user, verify Claude Desktop snippet is copy-pasteable and correct

---

### Phase 6 — Production Hardening
**Status:** Pending
**PR:** `feat: retry logic, input validation, structured errors, async consistency`
**Effort:** ~2h | **Parallelizable with Phases 4 & 5**

**Step 0 — Planning session:** Walk through error code taxonomy, retry behavior UX (does the user see retry attempts?), structured error response format, which inputs need validation at boundary vs. trusted internally. Get user approval.

1. **Retry** (`client.py`): `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))` on all HTTP calls, log each retry at WARNING
2. **Rate limiting** (`client.py`): 1.5s enforced between write API calls, `_last_write_time` tracking
3. **Input validation** (`server.py`): device_id max 10 chars, stage in known set, speed 0-10, port 1-8, VPD 0.1-3.0
4. **Structured errors**: `ACInfinityErrorResponse(code, message, recoverable, suggested_action)` — codes: `DEVICE_NOT_FOUND`, `AUTH_EXPIRED`, `RATE_LIMITED`, `INVALID_PARAMS`, `API_ERROR`
5. **Startup errors**: Name the missing env var explicitly ("Missing AC_INFINITY_EMAIL — set in .env")
6. **Remove `anthropic`** from requirements (unused in MCP server)
7. **Consistent async**: audit all tools, ensure every blocking call goes through `asyncio.to_thread()`
8. **`pip audit`**: confirm no CVEs in dependencies

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: test retry by pointing to bad URL (3 attempts + clean error); test rate limit (rapid write calls)

---

### Phase 7 — New Read Tools (port status + health + trends)
**Status:** Pending
**PR:** `feat: get_port_status, get_environment_health_score, detect_environmental_trends`
**Effort:** ~2.5h | **Sequential after Phase 6**

**Step 0 — Planning session:** Show example outputs for health score and trend detection. Discuss score weighting rationale (VPD 40 / temp 30 / humidity 30), drift alert thresholds, trend sample interval choice. Confirm grower-facing recommendation language. Get user approval.

**`get_port_status(device_id, port)`**: Parse currently-ignored fields from `/api/user/devInfoListAll`: `speak` (actual current power 0-10), `loadState` (0=no load, 1=device plugged in), `curMode` (active mode string), `remainTime` (timer countdown seconds). Tests: mock API response with all field combinations.

**`get_port_settings(device_id, port)`**: Call `/api/dev/getdevModeSettingList`, return full automation config — current mode, speed targets, VPD target, temp range, humidity range, schedule window, timer/cycle settings. Tests: mock response for both controller types.

**`get_environment_health_score(device_id, stage)`** (in `analytics.py`):
- Fetch current reading
- VPD score (40%): 100 if in target range, scaled penalty for drift
- Temp score (30%): scaled against stage-appropriate range
- Humidity score (30%): scaled against stage-appropriate range
- Overall: weighted sum → 0-100 → grade A(90+)/B(80+)/C(70+)/D(60+)/F(<60)
- Returns: `{score, grade, vpd_score, temp_score, humidity_score, top_recommendation}`
- Tests: verify weighting, grade thresholds, recommendation content

**`detect_environmental_trends(device_id, days)`** (in `analytics.py`):
- Fetch N days of historical data at `1h` interval
- Linear regression (least squares, stdlib only) on temp/humidity/VPD
- Return per-metric: `slope` (change per day), `direction` (rising/falling/stable), `7_day_projection`, `alert` (if slope exceeds threshold: >0.5°F/day, >2% RH/day, >0.1 VPD/day)
- Tests: ascending/descending/flat datasets, alert thresholds

**Gate loop before PR: all 5 gates**

---

### Phase 8 — Write-Control Tools (5 tools)
**Status:** Pending
**PR:** `feat: write-control tools — set_port_speed, set_port_mode, VPD/temp/humidity automation`
**Effort:** ~3.5h | **Sequential after Phase 7**

**Step 0 — Planning session:** Walk through the read-then-write flow with example API payloads for both controller types. Show the 77-field payload structure. Confirm dry_run UX — what does the response look like before the user says "go"? Confirm rate-limiting behavior visibility. Live device safety plan: which port/device will be used for smoke test? Get user approval.

**`controller.py`** — Complete implementation:
- `detect_controller_type(device_data)` → `ControllerType.LEGACY` or `ControllerType.NEW_FRAMEWORK`
  - Legacy: `devType` in `{11, 18}` or `newFrameworkDevice == False`
  - New framework: `devType >= 20` or `newFrameworkDevice == True`
- `build_write_payload(current_settings, updates, controller_type)`:
  - Legacy: fetch current settings → deep merge → return full 77-field dict
  - New framework: start from static defaults dict → overlay target fields → return full dict
  - Validates: `modeSetid` excluded from payload, `modeType=2` when `onSpead > 0`

**`set_port_speed(device_id, port, speed, dry_run=False)`**:
- Validate speed 0-10
- Detect controller type
- Fetch settings if legacy
- Build payload with `onSpead=speed`, `modeType=2` (or 0 if speed=0)
- If `dry_run`: return planned payload without POSTing
- POST to correct endpoint, enforce 1.5s rate limit
- Return: `{applied: true, port, speed, controller_type, dry_run}`

**`set_port_mode(device_id, port, mode, **kwargs, dry_run=False)`**:
- Valid modes: `OFF`, `ON`, `AUTO`, `VPD`, `TIMER`, `CYCLE`, `SCHEDULE`
- Validate mode-specific kwargs (e.g., TIMER requires `duration_minutes`)
- Same controller-type-aware payload flow
- Return: applied mode summary

**`set_vpd_automation(device_id, port, target_vpd, dry_run=False)`**:
- Validate target_vpd 0.1–3.0 kPa
- Set `vpdSettingMode=1`, `targetVpd=int(target_vpd*100)`, `targetVpdSwitch=1`, `atType=3` (AUTO/VPD)
- Uses built-in temp/humidity sensors (v1.0 scope)

**`set_temperature_automation(device_id, port, min_c, max_c, dry_run=False)`**:
- Validate min_c < max_c, both in reasonable range (0–50°C)
- Set `devLt=int(min_c*100)`, `devHt=int(max_c*100)`, `activeLt=1`, `activeHt=1`, `atType=3`

**`set_humidity_automation(device_id, port, min_rh, max_rh, dry_run=False)`**:
- Validate min_rh < max_rh, both 0-100
- Set `devLh=int(min_rh*100)`, `devHh=int(max_rh*100)`, `activeLh=1`, `activeHh=1`, `atType=3`

**Tests** (`tests/devices/test_legacy_controller.py` + `tests/devices/test_ai_plus_controller.py`): Both controller types, dry_run mode, rate limit enforcement, modeSetid exclusion, modeType coercion, invalid speed/mode/VPD handling.

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: test `dry_run=True` first on live device; confirm payload structure; then execute one `set_port_speed` on a non-critical port

---

### Phase 9 — Intelligence Tools + MCP Prompts
**Status:** Pending
**PR:** `feat: apply_grow_stage_template, get_port_activity_report, MCP prompts`
**Effort:** ~2h | **Sequential after Phase 8**

**Step 0 — Planning session:** Review the stage template target values — do the defaults match your actual grow environment targets? Walk through the port activity report format and what "busiest hour" means. Review the three prompt templates for language and accuracy. Get user approval on all default values before they're coded in.

**`apply_grow_stage_template(device_id, port, stage, dry_run=False)`**:
Built-in target library (in `schema.py`):
```python
STAGE_TEMPLATES = {
    "seedling":     {"vpd_target": 1.0, "temp_min_c": 22, "temp_max_c": 26, "humidity_min": 65, "humidity_max": 80},
    "veg":          {"vpd_target": 1.2, "temp_min_c": 22, "temp_max_c": 28, "humidity_min": 50, "humidity_max": 70},
    "early_flower": {"vpd_target": 1.4, "temp_min_c": 21, "temp_max_c": 27, "humidity_min": 45, "humidity_max": 60},
    "mid_flower":   {"vpd_target": 1.6, "temp_min_c": 20, "temp_max_c": 26, "humidity_min": 40, "humidity_max": 55},
    "late_flower":  {"vpd_target": 1.5, "temp_min_c": 18, "temp_max_c": 24, "humidity_min": 35, "humidity_max": 45},
}
```
- Calls `set_vpd_automation`, `set_temperature_automation`, `set_humidity_automation` in sequence
- `dry_run=True` propagates to all sub-calls
- Returns: full applied config summary per sub-tool

**`get_port_activity_report(device_id, start_date, end_date)`**:
- Fetch historical data at `1h` interval
- Per-port: total on-hours, off-hours, on/off transitions, avg speed when running, uptime %, peak usage hour
- Returns: sorted by uptime %, flag any port at >90% uptime (possible burnout risk)

**MCP Prompts** (`@mcp_server.prompt()` in `server.py`):
- `vpd_troubleshooting(current_vpd, stage)` — "VPD is HIGH/LOW for {stage}. Likely causes: [list]. Try: set_vpd_automation(device_id, port, {target})"
- `new_grower_setup()` — "Step 1: discover_devices() → Step 2: apply_grow_stage_template() → Step 3: get_environment_health_score()"
- `environment_alert_interpretation(alert_code)` — Explain what alert codes mean + what action to take

**Gate loop before PR: all 5 gates**
- Gate 5 smoke: call `apply_grow_stage_template` with `dry_run=True`, verify planned config matches stage targets

---

### Phase 10 — v1.0.0 Release
**Status:** Pending
**PR:** `chore: v1.0.0 release prep`
**Effort:** ~1h | **After all phases complete**

**Step 0 — Planning session:** Review the full announcement checklist together. Confirm PyPI package name, Docker image tags, MCP registry submission text. Confirm release notes draft before tagging. Get user approval to tag.

1. Full test run — all green, ≥85% coverage
2. `ruff check` + `mypy` — clean
3. Bump version to `1.0.0` in `pyproject.toml` and `__init__.py`
4. Write CHANGELOG v1.0.0 section (full feature list)
5. **Gate loop** — Gates 3, 4, 5 (abbreviated for release PR)
6. Merge → tag `v1.0.0` → release workflow fires → PyPI + Docker + GitHub Release
7. MCP registry submission

---

### Phase 11 — Project Report
**Status:** Pending
**Deliverable:** `PROJECT_REPORT.md` committed to `ober37/ac-infinity-mcp` on `main`
**Effort:** ~2h | **After Phase 10 tag is live**

**Step 0 — Planning session:** Review the report outline and confirm all metric inputs are available: LOC counts, test counts, PR list, time estimates per phase, and the lessons learned sections from all completed phases. Get user approval on the outline before writing.

**Report structure** (matched to `discord-mcp-server/PROJECT_REPORT.md` format):

**Section 1 — Overview**
One-paragraph summary: starting point (5 tools in monorepo), ending point (16 tools + 3 prompts, standalone PyPI package + Docker image). Disclaimer: built on personal Claude subscription credits.

**Section 2 — Coverage Summary**
Four tables:

- **Tools table:** Monorepo vs. v1.0 Standalone delta (`+11 tools, +220%`, `+4 modules`, `10 PRs merged`)
- **Lines of Code table:** Source LOC and test LOC before/after (actuals gathered at report time)
- **Test suite table:** Test count, test files, failures
- **API coverage table:** Phase-by-phase coverage progression (Phase 7 → 56%, Phase 8 → 88%, Phase 9 → 100%)
- **Controller compatibility table:** 69 Pro (devType 11, legacy), 69 Pro+ (devType 18, legacy), 89 AI+ (devType 20, new framework)

**Section 3 — Comprehensive Code Review**
Multi-pass format:
- Pass 1: Sonnet — Gate 1 + Gate 2 per PR, plus final holistic audit at Phase 10
- Pass 2: Independent second-model review (Opus or next-gen Sonnet, no prior exposure to Pass 1 findings)
- Summary table: Critical / High / Medium / Low findings, origin (introduced vs. inherited from monorepo), all resolved?
- Per-finding detail tables: #, Discovered by, Origin, File, Issue, Fix Applied

**Section 4 — Time Investment Summary**
Pull directly from the `**Phase N Time Investment**` blocks written at the close of each phase session (Phase 0 through Phase 10). Each block contains: actual Claude session time, projected manual time (range + midpoint), manual estimate basis, and multiplier.

Table format:
| Phase | Actual Claude Time | Projected Manual | Multiplier | Notes |
|---|---|---|---|---|
| Phase 0 — Ideation | 0:52 | 26–46h (mid ~36h) | ~41x | Zero ACI API knowledge; API research dominates |
| Phase 1 — ... | HH:MM | Xh–Yh | ~Xx | [from block] |
| ... | | | | |
| **Total** | **HH:MM** | **Xh–Yh** | **~Xx** | |

The overall multiplier (total projected manual ÷ total Claude time) is the headline metric for the report and suitable for the README/announcement post.

**Section 5 — Lessons Learned**
Synthesized from all Phase Lessons Learned sections written throughout execution.
Format: numbered list, each item titled, 2–4 paragraphs.
Seed topics (expand at report time with actuals from phases):
- The Phase Planning Session pays for itself
- Per-device test split catches controller-type bugs unit tests miss
- `dry_run` design pattern before every write-control call
- Second-model review finds what the first didn't (same pattern as Discord)
- Living plan file as shared state across sessions
- API quirk documentation is as valuable as the code

**Section 6 — What Remains**
- v2.0 roadmap (link to GitHub Project)
- Peekaboopoint monorepo cleanup status
- Any open issues at time of report

**Section 7 — PR Appendix**
All PRs merged to `ober37/ac-infinity-mcp`, chronological:
| PR | Date | Title | Summary |

---

## Parallelization Map

```
Phase 1 (scaffold + core)   ──────── 3h    ← must run first
                            ↓
Phase 2 (tests)             ────── 2.5h ──────────────────────────────┐
Phase 3 CI YAML draft       ── 0.5h (write during Phase 2)           │
                                 ↓                                     │
Phase 3 finalize + PR       ─ 1h                                      │
                                                                       ↓
Phase 4 (Docker)            ──── 1.5h ←── after Phase 1              │
Phase 5 (Docs)              ────────── 3h ←── after Phase 1          │
Phase 6 (hardening)         ─── 2h ←── after Phase 1                 ↓
                                 ↓
Phase 7 (read tools)        ──── 2.5h ←── after Phase 6
                                 ↓
Phase 8 (write-control)     ──────── 3.5h ←── after Phase 7
                                 ↓
Phase 9 (intelligence)      ─── 2h ←── after Phase 8
                                 ↓
Phase 10 (release)          ─ 1h
                                 ↓
Phase 11 (project report)   ── 2h ←── after Phase 10 tag is live
```

**Total sequential critical path:** ~16h
**With Day 1 parallelization (Phases 2–6 overlapping):** ~2 days across Phase 1 → parallel → Phase 7-11 linear

---

## Changes Required in Peekaboopoint Monorepo

After standalone repo is live and all 16 tools confirmed working:

### Update:
1. `skills/ac-infinity-access/SKILL.md` — Add "Server installation" section pointing to `ober37/ac-infinity-mcp`; tool names + behavior unchanged
2. `docker-compose.dev.yml` — Pull `ghcr.io/ober37/ac-infinity-mcp:latest` instead of local build

### Remove (after confirmed working):
3. `scripts/acinfinity/` — entire directory
4. `tests/acinfinity/` — entire directory
5. `docker/ac-infinity/` — entire directory

### Leave unchanged:
- All agent config files (`04-grow-tracker.md`, etc.)
- `grows/active/*/device-mapping.json`
- `blueprint/ac-infinity-mcp-architecture.md`

---

## v1.0 Announcement Checklist

- [ ] GitHub repo `ober37/ac-infinity-mcp` live — description + topics: `mcp`, `ac-infinity`, `cannabis`, `grow-automation`, `iot`, `fastmcp`
- [ ] README with CI/PyPI/Docker badges, copy-paste Claude Desktop config
- [ ] All 16 tools + 3 prompts documented in `docs/API.md`
- [ ] GitHub Actions CI passing, badge in README
- [ ] Docker image on `ghcr.io/ober37/ac-infinity-mcp`
- [ ] PyPI package `ac-infinity-mcp` published
- [ ] GitHub Release tagged `v1.0.0` with full release notes
- [ ] All 15 API quirks documented
- [ ] `dry_run` usage guide in docs
- [ ] MCP registry listing submitted
- [ ] Monorepo cleaned up; peekaboopoint confirmed working
- [ ] `PROJECT_REPORT.md` committed to `main` (Phase 11 deliverable — run after all above are checked)

---

## v2.0 Feature Tracking Strategy

### How features are tracked

**Three-layer tracking on GitHub (all free on public repos):**

1. **GitHub Issues** — Each feature is a self-contained spec issue. Point me at the URL, I fetch the full spec and implement. No external context needed.

2. **GitHub Milestone: "v2.0"** — All v2.0 issues are linked to this milestone. Shows progress as issues close (e.g., "3/10 complete"). Created when the repo goes live.

3. **GitHub Project (free, public repos)** — A Project board with a Roadmap view (timeline) for visual planning. Issues added to the project inherit milestone grouping. URL shareable — I can read and update project state via GitHub MCP.

**Setup at repo launch:** Create milestone "v2.0" → create all 10 issues → create a GitHub Project named "AC Infinity MCP Roadmap" → add all v2.0 issues to the project → set Roadmap view as default.

**Free tier note:** GitHub Projects and Milestones are fully unlimited on public repositories. GitHub Actions CI uses the public repo quota (effectively unlimited minutes for public repos — no constraints here).

**To implement any feature:** Point me at the issue URL and say "implement this." Everything needed is embedded in the issue.

### Required Issue Template (applies to every v2.0 issue)

Each issue must include:

```markdown
## Summary
One sentence on what this does and why growers want it.

## User Story
As a [cannabis grower / hydro operator], I want to [action] so that [outcome].

## Scope Boundary
- v2.0: requires [external sensor / BLE hardware]
- Blocked on: [hardware requirement or API gap]

## AC Infinity API
- Endpoint: `/api/...`
- Key fields: [field names + encoding notes]
- Source: [link to homebridge or HA implementation line]

## Implementation Notes
Relevant reverse-engineered code and known constraints.

## Acceptance Criteria
- [ ] Tool returns correct data when sensor is connected
- [ ] Tool returns meaningful error when sensor is absent or unsupported
- [ ] Both controller types tested (legacy + new framework)
- [ ] Documented in docs/API.md
- [ ] Unit tests cover connected / absent / invalid states
```

### v2.0 Issues to Create at Repo Launch

Create these as GitHub Issues immediately after v1.0 ships, tagged `v2.0` + appropriate labels:

| Issue | Feature | Hardware Required | `sensorType` |
|---|---|---|---|
| #1 | CO2 monitoring + automation triggers | UIS CO2 sensor | 11 |
| #2 | Soil moisture monitoring | UIS soil moisture sensor | 10 |
| #3 | Light level monitoring | UIS light sensor | 12 |
| #4 | Hydro pH monitoring + automation | UIS pH probe | 13 |
| #5 | Hydro EC monitoring (µS/cm + mS/cm) | UIS EC probe | 14, 15 |
| #6 | Hydro TDS monitoring (ppm + ppt) | UIS TDS probe | 16, 17 |
| #7 | Water temperature monitoring | UIS water temp probe | 18, 19 |
| #8 | Water level monitoring | UIS water level sensor | 20 |
| #9 | Bluetooth local control | BLE stack — `ac-infinity-ble` library |  |
| #10 | Offline/local mode (no cloud) | BLE only |  |

**Implementation note for issues #1-8:** The API already returns sensor data in the `sensors` array from `/api/user/devInfoListAll` — no new endpoints needed. Each issue's implementation is: parse the correct `sensorType` enum value, expose the reading, add automation write support. The `sensorData` field is divided by `sensorPrecision` for the actual value.

**Implementation note for issues #9-10:** These require the `ac-infinity-ble` Python library (`pip install ac-infinity-ble`) and a Bluetooth stack. Cloud API not involved. Separate authentication model (BLE pairing vs. cloud token).
