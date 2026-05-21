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
| 4 | Full API Documentation + Read Tool Polish | 🔲 Pending | — |
| 5 | CI/CD Pipeline | 🔲 Pending | — |
| 6 | Write Tools Foundation | 🔲 Pending | — |
| 7 | Write Tools MCP Layer | 🔲 Pending | — |
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

**Status:** 🔲 Pending

### Scope
- `.github/workflows/ci.yml` — ruff, mypy, pytest, pip-audit on every PR
- `.github/workflows/codeql.yml` — CodeQL security scan
- Dependabot config
- Branch protection rules (document in CONTRIBUTING.md)

---

## Phase 6 — Write Tools Foundation

**Status:** 🔲 Pending

### Scope
- Implement `controller.py`: `detect_controller_type` (already stubbed), `build_write_payload` (legacy read-before-write + AI+ static payload)
- Add `client.py` write methods: `get_mode_settings`, `set_port_mode`
- No MCP tools yet — foundation + tests only
- All 15 API quirks relevant to writes must be handled (quirks 11–15)

---

## Phase 7 — Write Tools MCP Layer

**Status:** 🔲 Pending

### Scope
- `set_port_speed(device_id, port, speed, dry_run=True)` MCP tool
- `set_port_on(device_id, port, dry_run=True)` MCP tool
- `set_port_off(device_id, port, dry_run=True)` MCP tool
- All tools default to `dry_run=True` and return the payload they _would_ send
- End-to-end wiring to client.py write methods

---

## Phase 8 — Write Tools Full Implementation

**Status:** 🔲 Pending

### Scope
- Complete `controller.py` `build_write_payload` for both legacy (all 77 params) and AI+ (static full payload)
- Timer modes, auto schedules, target-VPD auto mode write tools
- `dry_run=False` path verified against live API
- Retry logic on 403 rate-limit responses

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
