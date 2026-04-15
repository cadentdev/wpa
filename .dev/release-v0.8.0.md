# Release Checklist: v0.8.0

**Started:** 2026-04-15 | **Project:** wpa (WordPress Automation)

## Current Step: Step 1 — Security Audit

| Step | Status | Notes |
|------|--------|-------|
| Pre-flight | [x] | Branch clean, Python tooling detected, 12 commits, 408 tests |
| 1. Security Audit | [~] | Launching RedTeam full swarm + Fabric threat model |
| 2. Triage Findings | [ ] | |
| 3. Fix Blockers | [ ] | |
| --- GATE: Security | [ ] | |
| 4. Test Coverage | [ ] | Expect 408 tests, 99% coverage |
| --- GATE: Quality | [ ] | |
| 5. Dependency Audit | [ ] | pip-audit clean at end of FeatureDev |
| 6. Documentation Final Pass | [ ] | Tick wpa-prd.md Phase 4 COMPLETE |
| 7. Version Bump | [ ] | 0.7.0 → 0.8.0 in pyproject.toml + __init__.py |
| 8. Release Notes | [ ] | Promote docs/RELEASE-NOTES-v080.md → RELEASE-NOTES.md |
| 9. PR Creation/Update | [ ] | PR #32 exists, update body |
| 10. Issue Triage | [ ] | |
| 11. Merge & Verify | [ ] | Merge commit (not squash) |
| --- GATE: CI | [ ] | |
| 12. Tag & GitHub Release | [ ] | v0.8.0 |
| 13. Post-Release | [ ] | LinkedIn draft + PyPI publish |
| 14. Branch Cleanup | [ ] | Delete claude/phase-4-tdd-implementation-vJMmZ |
| 15. Retrospective | [ ] | |

## Features Included

- **Comments CRUD + moderation** (Phase 4, FeatureDev complete)
- **Taxonomy Terms CRUD** (Phase 4, FeatureDev complete)
- **Category/Tag aliases** (Phase 4, FeatureDev complete)
- Deferred: Meta handler → issue #33

## Findings

**Audit (Step 1) — 2026-04-15**

Blockers: **0** / High: 0 / Medium: 5 / Low: 5 / Info: 3

Triage:
- **Blocker:** none
- **Should-fix (post-release, file as issues):**
  - M1 `--password` CLI flag leaks via argv/ps/history → deprecate, add `--password-stdin`
  - M2 No response-size cap / total_pages unbounded → OOM defense
  - M3 Redirect handling — add `allow_redirects=False` on writes, reject `https→http` downgrade
  - M4 No central endpoint traversal guard → defense-in-depth sanitizer in api.py
- **Nice-to-have:** L1-L5 (minor), ANSI passthrough in formatter
- **Not a finding:** H1 (keyring drift) withdrawn — audit brief was wrong, code uses .env@0600 as designed
- **Deliberate:** M5 unpinned runtime deps — documented in release notes, end-users always pull patched versions

No security fixes required before merge. File 4 follow-up issues (M1-M4) post-release.

## Detours

<!-- Unplanned work between steps -->
