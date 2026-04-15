# Feature Checklist: Phase 4 — Comments and Terms (v0.8.0)

**Issue:** (none — worked directly from PRD)
**Branch:** `claude/phase-4-tdd-implementation-vJMmZ`
**Started:** 2026-04-14 (Claude Code Web session)
**Resumed:** 2026-04-15 (local session, flicky)
**PRD reference:** `wpa-prd.md` §7 Phase 4

## Current Phase: 9 — Retrospective

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Describe Feature | [x] | No GH issue — worked from PRD directly. Per Neil, agreed. |
| 2. Implementation Plan | [x] | CCW followed PRD §6.2 Tier 2 + §7 Phase 4 as the plan. |
| 3. Implement & Test | [x] | TDD red→green. 91 new tests. `wpa/comment.py` + `wpa/term.py` + `tests/test_comment.py` + `tests/test_term.py` + `wpa/cli.py` wiring. Commits `d36b146`, `b88b057`. Meta handler **deferred** to follow-up (tracked as #33). |
| 4. Refactor | [x] | Commit `f71ca00`. Caught a real bug in `_resolve_endpoint` — `re.IGNORECASE` on the slug regex accepted `POST_TAG`/`Category` but the case-sensitive `_TAXONOMY_ENDPOINTS` lookup fell through, routing to `/wp/v2/POST_TAG` (404). Fix lowercases before lookup. Also deduped `_extract_rendered` in `comment.py` by importing from `wpa.post` (matches the `page.py` precedent). Added 3 TDD tests. 405 tests, 99% coverage. |
| 5. Light Security Review | [x] | `bandit -r wpa/` — **zero findings** (3100 LOC scanned). `pip-audit` — upgraded venv: `requests 2.33.1`, `cryptography 46.0.7`, `pygments 2.20.0`, `pytest 9.0.3`. Runtime deps in pyproject are unpinned so end-users always pull patched versions on fresh install. Manual audit: `_resolve_endpoint` regex rejects `/`, `..`, shell metacharacters; all ID validators reject bool + non-positive; no eval/exec/subprocess/file-I/O in new modules; REST body fields passed through (kses server-side). No vulnerabilities found. |
| 6. Create PR | [x] | **PR #32** — https://github.com/cadentdev/wpa/pull/32. All 6 CI jobs green on the final commit `658e0cf` (ubuntu 3.9/3.11/3.12/3.13, macos 3.12, windows 3.12). 6 commits ahead of main. |
| 7. Team Review | [x] | Neil confirmed: tests sufficient, CI green, no GH issue retrofit needed (PR serves as documentation). Follow-up work filed as **#33 meta handler**, **#34 comment count**, **#35 term merge**. Two initial follow-up issues landed on upstream PAI by mistake (#1070, #1071) and were re-filed after a `gh issue create` backgrounded-subshell cwd bug — logged for Phase 9 retro. |
| 8. Docs & Help | [x] | Three sub-tasks done: (a) `examples/bootstrap-site.sh` extended with Section 5 (Comments — create, full moderation state machine, update, list, trash, force-delete) and Section 6 (Terms/Categories/Tags — alias + generic forms, fetch, update, list, delete) in commit `e0c769b`. (b) README.md + CLAUDE.md + RELEASE-NOTES-v080.md updated in the same commit: new Manage Comments and Manage Terms README sections, coverage badge 75%→99%, test count 402→405, release notes stats refreshed with bug-fixes section and security findings, follow-up issues linked. (c) Phase 8c live smoke test against CT 118: rolled back via `pct rollback 118 wpa_baseline` (snapshot from 2026-04-14), ran the updated `bootstrap-site.sh` **three times** — first run surfaced an invisible-but-real WP REST API asymmetry bug (`status=approved` query param must actually be `status=approve`), second run reproduced it, third run confirmed the fix. Bug fix in commit `658e0cf`: `list_comments` now normalizes `approved` → `approve` at the boundary. 3 TDD tests added. 408 tests passing. Also wrote and ran `pve_ct_rollback.yml` in cadentdev/ansible (10 tasks, ok=10 changed=2, verify_url probe succeeded), filed as **cadentdev/ansible#8**. |
| 9. Retrospective | [~] | Resume here. Lessons to capture: (1) retroactive progress checklist on CCW handoff; (2) `gh issue create` backgrounded-subshell cwd gotcha; (3) Jinja2 self-reference recursion in new Ansible playbook vars (third recurrence — ProvisionWP, now this); (4) WP REST API `status=approved`/`status=approve` asymmetry that only surfaced via live testing — argues for Phase 8c being a hard gate, not optional; (5) smoke test must list post-approve BEFORE any content edit, because WP moderation can re-run on update. |
| 7. Team Review | [ ] | |
| 8. Docs & Help | [ ] | Three sub-tasks: (a) update `examples/bootstrap-site.sh` with new comment + term sections for v0.8.0 smoke test, (b) update README.md + verify `--help` text + draft RELEASE-NOTES.md entry from the existing `docs/RELEASE-NOTES-v080.md`, (c) live smoke test on rolled-back CT 118. |
| 9. Retrospective | [ ] | |

## Detours

<!-- Log unplanned but valuable work that happened between phases -->

### 2026-04-15: CCW handoff — no checklist file, retroactive tracker

The Claude Code Web session that built v0.8.0 Phase 4 did **not** create a progress checklist file on the branch, so the local resume had to reconstruct the state from `git log`, `docs/RELEASE-NOTES-v080.md`, and the PRD. This is exactly the scenario Progress Tracking v1.4 was designed to prevent (see `FeatureDevelopmentChecklist.md` Provenance). Fixed by creating this file after the fact with Phases 1–3 marked `[x]` based on verified artifacts (tests passing, release notes present, commits on branch). **Log this in the Phase 9 retrospective** as a reason to add a Phase 1 gate: "If resuming a branch from a different agent session, the first act must be to create or update the checklist file."

### 2026-04-15: Deferred meta handler — confirmed scope decision

PRD Phase 4 called for a "reusable meta handler" for `meta add/get/update/delete/list` across post/page/comment/term/user. CCW's `docs/RELEASE-NOTES-v080.md` notes this was deferred "pending a closer look at how REST-exposed meta varies across sites and plugins." Confirmed with Neil on 2026-04-15: **meta handler deferred to a follow-up sprint**, not blocking v0.8.0 ship. v0.8.0 ships comment + term + category/tag aliases only. Tracked as issue #33.

### 2026-04-15: Follow-up issues filed

Three follow-up enhancements identified during Phase 7 team review and filed for post-v0.8.0 work:
- **#33** — Meta handler (deferred PRD scope)
- **#34** — `wpa comment count` (moderation queue convenience; low priority)
- **#35** — `wpa term merge` (taxonomy cleanup with children handling + dry-run; medium priority)

### 2026-04-15: gh issue create wrong-repo incident

Filed the three follow-up issues via a parallel `gh issue create` batch. The first call was prefixed with `cd ~/Repos/cadentdev/wpa && gh issue create ... &`; the subsequent two were plain `gh issue create ... &`. In bash, `cd` only applies before the first `&`, so the two backgrounded calls ran in the default cwd (`~/.claude`) and `gh` defaulted to that repo's remote — `danielmiessler/Personal_AI_Infrastructure` upstream — filing #1070 and #1071 against PAI by mistake. Closed both upstream issues with an apology and re-filed correctly using explicit `-R cadentdev/wpa` on each call. **Lesson for Phase 9 retro:** when batching `gh` across multiple backgrounded shells, always pass `-R <owner>/<repo>` explicitly rather than relying on cwd inheritance.
