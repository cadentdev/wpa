# Feature Checklist: Phase 4 — Comments and Terms (v0.8.0)

**Issue:** (none — worked directly from PRD)
**Branch:** `claude/phase-4-tdd-implementation-vJMmZ`
**Started:** 2026-04-14 (Claude Code Web session)
**Resumed:** 2026-04-15 (local session, flicky)
**PRD reference:** `wpa-prd.md` §7 Phase 4

## Current Phase: 4 — Refactor

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Describe Feature | [x] | No GH issue — worked from PRD directly. Per Neil, agreed. |
| 2. Implementation Plan | [x] | CCW followed PRD §6.2 Tier 2 + §7 Phase 4 as the plan. |
| 3. Implement & Test | [x] | TDD red→green. 91 new tests. `wpa/comment.py` + `wpa/term.py` + `tests/test_comment.py` + `tests/test_term.py` + `wpa/cli.py` wiring. Commits `d36b146`, `b88b057`. Meta handler **deferred** to follow-up (agreed). |
| 4. Refactor | [~] | Resume here. Need to audit for dead code, dup logic, import ordering, type annotations, edge cases in `_resolve_endpoint` and the comment moderation wrappers. |
| 5. Light Security Review | [ ] | Must run `bandit -r wpa/` + `pip-audit`. Review `_resolve_endpoint` taxonomy slug validation for path traversal. Audit content field handling in comment create/update. |
| 6. Create PR | [ ] | Branch has never been pushed as a PR. Need to push and open against `main` referencing PRD Phase 4. |
| 7. Team Review | [ ] | |
| 8. Docs & Help | [ ] | Three sub-tasks: (a) update `examples/bootstrap-site.sh` with new comment + term sections for v0.8.0 smoke test, (b) update README.md + verify `--help` text + draft RELEASE-NOTES.md entry from the existing `docs/RELEASE-NOTES-v080.md`, (c) live smoke test on rolled-back CT 118. |
| 9. Retrospective | [ ] | |

## Detours

<!-- Log unplanned but valuable work that happened between phases -->

### 2026-04-15: CCW handoff — no checklist file, retroactive tracker

The Claude Code Web session that built v0.8.0 Phase 4 did **not** create a progress checklist file on the branch, so the local resume had to reconstruct the state from `git log`, `docs/RELEASE-NOTES-v080.md`, and the PRD. This is exactly the scenario Progress Tracking v1.4 was designed to prevent (see `FeatureDevelopmentChecklist.md` Provenance). Fixed by creating this file after the fact with Phases 1–3 marked `[x]` based on verified artifacts (tests passing, release notes present, commits on branch). **Log this in the Phase 9 retrospective** as a reason to add a Phase 1 gate: "If resuming a branch from a different agent session, the first act must be to create or update the checklist file."

### 2026-04-15: Deferred meta handler — confirmed scope decision

PRD Phase 4 called for a "reusable meta handler" for `meta add/get/update/delete/list` across post/page/comment/term/user. CCW's `docs/RELEASE-NOTES-v080.md` notes this was deferred "pending a closer look at how REST-exposed meta varies across sites and plugins." Confirmed with Neil on 2026-04-15: **meta handler deferred to a follow-up sprint**, not blocking v0.8.0 ship. v0.8.0 ships comment + term + category/tag aliases only.
