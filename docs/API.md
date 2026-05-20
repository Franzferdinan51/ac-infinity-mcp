# AC Infinity API Reference

Full tool documentation coming in Phase 5.

## Security Note

The AC Infinity cloud API uses HTTP only (no TLS). This is a known limitation
of the upstream API and is an accepted risk for local/trusted network deployments.
See `docs/DEPLOYMENT.md` for HTTPS reverse-proxy setup options.

## Known API Quirks

All 15 quirks documented in full in Phase 5. Summary:

1. `appPasswordl` — intentional typo in auth parameter (lowercase `l` at end)
2. Password silently truncated to 25 chars
3. `pageNum` in history API ignored — use time-cursor pagination
4. Temp/humidity/VPD values divided by 100 in API responses
5. Port speeds encoded as 4-bit nibbles in `portSpead` bitmask; `0xF` = ON for toggle devices
6. `portStatus` bitmask (1 bit per port) = automation-triggered state
7. `devCode` (string) ≠ `devId` (numeric) — history API requires `devId`
8. API base is HTTP only — document security limitation
9. Historical API returns max ~1257 records/day regardless of `pageSize`
10. `vpdnums` field in device info; `vpdNums` in history records (different casing)
11. Write-control: NEVER include `modeSetid` field for legacy controllers → 403 error
12. Write-control: Must set `modeType=2` when `onSpead > 0` or change doesn't persist
13. Write-control: Legacy controllers require read-before-write (all 77 params must be sent)
14. Write-control: AI+ controllers (`newFrameworkDevice=true`) use static full payload
15. Rate limit: 1.5s minimum between write API calls (returns 403 "Data saving failed" if exceeded)
