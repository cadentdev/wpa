# Feature Checklist: Phase 4 — Comments and Terms (v0.8.0)

**Issue:** (none — worked directly from PRD)
**Branch:** `claude/phase-4-tdd-implementation-vJMmZ`
**Started:** 2026-04-14 (Claude Code Web session)
**Resumed:** 2026-04-15 (local session, flicky)
**PRD reference:** `wpa-prd.md` §7 Phase 4

## Current Phase: ALL DONE

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Describe Feature | [x] | No GH issue — worked from PRD directly. Per Neil, agreed. |
| 2. Implementation Plan | [x] | CCW followed PRD §6.2 Tier 2 + §7 Phase 4 as the plan. |
| 3. Implement & Test | [x] | TDD red→green. 91 new tests. `wpa/comment.py` + `wpa/term.py` + `tests/test_comment.py` + `tests/test_term.py` + `wpa/cli.py` wiring. Commits `d36b146`, `b88b057`. Meta handler **deferred** to follow-up (tracked as #33). |
| 4. Refactor | [x] | Commit `f71ca00`. Caught a real bug in `_resolve_endpoint` — `re.IGNORECASE` on the slug regex accepted `POST_TAG`/`Category` but the case-sensitive `_TAXONOMY_ENDPOINTS` lookup fell through, routing to `/wp/v2/POST_TAG` (404). Fix lowercases before lookup. Also deduped `_extract_rendered` in `comment.py` by importing from `wpa.post` (matches the `page.py` precedent). Added 3 TDD tests. |
| 5. Light Security Review | [x] | `bandit -r wpa/` — **zero findings** (3100 LOC scanned). `pip-audit` — upgraded venv: `requests 2.33.1`, `cryptography 46.0.7`, `pygments 2.20.0`, `pytest 9.0.3`. Runtime deps in pyproject are unpinned so end-users always pull patched versions on fresh install. Manual audit found nothing. |
| 6. Create PR | [x] | **PR #32** — https://github.com/cadentdev/wpa/pull/32. All 6 CI jobs green on every push. |
| 7. Team Review | [x] | Neil confirmed: tests sufficient, no GH issue retrofit needed (PR serves as documentation). Follow-up work filed as **#33 meta handler**, **#34 comment count**, **#35 term merge**. |
| 8. Docs & Help | [x] | 8a bootstrap-site.sh extended with Sections 5 (Comments) and 6 (Terms/Categories/Tags). 8b README + CLAUDE.md + release notes updated. 8c live smoke test against CT 118 surfaced the WP REST API `status=approved` asymmetry — fixed TDD-style. Later iterations added the 256x256 fixture image and a persistent-plus-transient two-comment pattern after Neil's browser-walk feedback. |
| 9. Retrospective | [x] | Full lessons captured below. FeatureDevelopmentChecklist.md updated with 5 propagated lessons. |

## Final ship stats

- **PR:** https://github.com/cadentdev/wpa/pull/32
- **Commits on branch:** 9 (2 CCW + 7 local resume)
- **Tests:** 408 passing, 99% coverage, `comment.py` 100%, `term.py` 100%
- **Bugs caught:** 2 (`_resolve_endpoint` case sensitivity, `list_comments` status-approved asymmetry) — one via refactor pass, one via live smoke test
- **Follow-up issues filed:** 3 in cadentdev/wpa (#33, #34, #35), 1 in cadentdev/ansible (#8 with PR #9)
- **Ansible playbook added:** `pve_ct_rollback.yml` in cadentdev/ansible PR #9
- **Live smoke test:** ran 5 full end-to-end runs against CT 118 during Phase 8c iterations

---

## Retrospective

### What went well

- **TDD discipline held even on a handoff branch.** The 91 tests CCW wrote were solid enough that the Phase 4 refactor pass could make confident changes — including catching a real routing bug — without regression fear.
- **Live testing surfaced a class of bug unit tests could not.** The WP REST API `status=approved`/`status=approve` asymmetry is literally undetectable by unit tests that mock the HTTP client. Phase 8c pulled its weight.
- **The rollback playbook wrote itself.** Doing the rollback ad-hoc first, then wrapping it in a playbook, produced a much better playbook than a "design on paper first" pass would have — we knew exactly which assertions mattered (snapshot-exists pre-flight), which failure modes to handle (CT already-running, `pct` sudo path), and what verification was useful (`pct status` poll + optional HTTP probe).
- **Progress checklist survived two context compactions and a fresh-session resume.** The Phase 4 CCW handoff, mid-session session compactions, and the Phase 8 live-test detour all stayed on-track because the `.dev/checklist-*.md` file was the single source of truth.

### What surprised us

1. **CCW didn't leave a progress checklist file.** The Claude Code Web session that built v0.8.0 Phase 4 wrote the code, the tests, and the release notes draft — but didn't create `.dev/checklist-phase-4-comments-terms.md`. The local resume had to reconstruct state from `git log`, release notes, and the PRD before it could confidently mark phases `[x]`. This is exactly the scenario Progress Tracking v1.4 was designed to prevent.

2. **`gh issue create` batching via backgrounded subshells silently filed issues in the wrong repo.** The pattern `cd ~/path && gh issue create ... &; gh issue create ... &; wait` only runs the `cd` before the first `&`. The subsequent backgrounded jobs run in the parent shell's cwd, and `gh` defaults to that cwd's git remote. Two issues landed in upstream `danielmiessler/Personal_AI_Infrastructure` (#1070, #1071) instead of `cadentdev/wpa` before we noticed.

3. **Jinja2 self-reference recursion in Ansible vars — third recurrence.** Writing `pve_host: "{{ pve_host | default('pve-terrace.lan') }}"` at the play vars level causes infinite recursion when the caller also passes `-e pve_host=...`. Known gotcha (fixed in the ProvisionWP playbook months ago), bit us again. The `_`-prefixed internal convention (`_pve_host` set from `{{ pve_host | default(...) }}`) is the standard fix.

4. **WP REST API comment status asymmetry is a silent footgun.** The `/wp/v2/comments` endpoint accepts `status=approve|hold|spam|trash` (imperative) as a query param but serializes responses as `status=approved|hold|spam|trash` (past tense for `approve` only). Only three of the four values round-trip; the fourth silently returns zero rows. Unit tests that mock `client.get_list` verify the param dict passed to the client, not what the upstream API accepts — so this was invisible until a live test hit it.

5. **WordPress comment content editing can re-trigger moderation.** Editing an approved comment's content via `wpa comment update` can transition it back to `hold` depending on site settings (moderation keywords, author trust, plugins). The smoke test's "list approved after edit" step was therefore unreliable as a test assertion; it should only assert on the approve → list path, not on the update → list path.

6. **1x1 fixture images pass every automated check and fail every human check.** The original `bootstrap-site.sh` PNG fixture was a 67-byte 1×1 red PNG. It uploaded fine, embedded fine, served at 200 OK with correct MIME type, `file` identified it as valid — but when Neil opened the rendered Featured post in a browser, he thought the image was broken. "Fit for purpose" for a smoke test that includes browser validation has to include "visible to a human at a glance."

7. **Two comments are better than one for a smoke test of a comment system.** A single comment that walks the full state machine and then gets deleted tests the mechanics but leaves nothing behind to prove the integration with the rendered site. A second persistent comment — created, approved, left in place — is the piece that makes "browse the site" a valid final check.

8. **`git add` on a gitignored-but-tracked file prints a misleading error.** `.dev/` is in `.gitignore` but checklist files are force-added to the tracked set. Running `git add .dev/checklist.md` on an *update* to an already-tracked file re-triggers the ignore hint ("The following paths are ignored by one of your .gitignore files"), even though the file is already in the index and the staging actually worked. `git diff --cached` is the reliable way to confirm the stage.

9. **Local-main commits on a PR-flow repo are recoverable but embarrassing.** I committed the Ansible playbook directly to local `main` before noticing the repo's merge-commit pattern (`Merge pull request #N`) indicated PR flow. Clean recovery: `git checkout -b feature/<name>` to move the branch pointer, then `git branch -f main origin/main` to reset local main. No damage, but a small process smell.

10. **Per-site memory defaults matter even for dev tools.** Running the claude-glass build earlier in the day hit OOM on the 3.7 GB flicky host; same root-cause family as "unit tests pass on my machine but the smoke test environment differs." Phase 8c live tests against a realistic target catch these.

### What would go smoother next time

- **Create the `.dev/checklist-*.md` file as the first resume action**, always, before reading any code. This should be literally the first tool call on resume.
- **When filing issues in parallel, always pass `-R owner/repo` explicitly.** Never rely on cwd inheritance across `&`.
- **Before writing Ansible play vars, mentally substitute a caller override.** If `vars: foo: "{{ foo | default(...) }}"` would recurse when `-e foo=bar` is passed, rename to `_foo` and reference `_foo` in tasks.
- **Treat Phase 8c (live testing) as a hard gate, not an afterthought.** Every module that talks to a remote API should have a live test that exercises at least the read-after-write path. The smoke test catches asymmetries the unit tests cannot.
- **Use visually meaningful smoke-test fixtures** — a bigger, recognizable placeholder image even if the test is "end-to-end upload + embed + serve."

### Still painful (won't necessarily improve)

- **Resume protocol on agent handoffs.** There's no way to force a previous agent to leave a `.dev/checklist-*.md` file. The best we can do is detect the absence on resume and fill it in retroactively. Document this as a resume-phase-zero step.
- **Mocked-client unit tests vs real-API behavior.** Even with the live test discipline, there's a large space of "valid-looking params the upstream API silently rejects" that we won't find until we try them. Live tests should be cheap to run so we run them often, not so expensive that we skip them — the `pve_ct_rollback.yml` playbook is exactly the infrastructure that makes this cheap.

## Detours

<!-- Log unplanned but valuable work that happened between phases -->

### 2026-04-15: CCW handoff — no checklist file, retroactive tracker

The Claude Code Web session that built v0.8.0 Phase 4 did **not** create a progress checklist file on the branch, so the local resume had to reconstruct the state from `git log`, `docs/RELEASE-NOTES-v080.md`, and the PRD. This is exactly the scenario Progress Tracking v1.4 was designed to prevent (see `FeatureDevelopmentChecklist.md` Provenance). Fixed by creating this file after the fact with Phases 1–3 marked `[x]` based on verified artifacts (tests passing, release notes present, commits on branch). **Captured in Phase 9 retro #1 above.**

### 2026-04-15: Deferred meta handler — confirmed scope decision

PRD Phase 4 called for a "reusable meta handler" for `meta add/get/update/delete/list` across post/page/comment/term/user. CCW's `docs/RELEASE-NOTES-v080.md` notes this was deferred "pending a closer look at how REST-exposed meta varies across sites and plugins." Confirmed with Neil on 2026-04-15: **meta handler deferred to a follow-up sprint**, not blocking v0.8.0 ship. Tracked as issue #33.

### 2026-04-15: Follow-up issues filed

Three follow-up enhancements identified during Phase 7 team review and filed for post-v0.8.0 work:
- **#33** — Meta handler (deferred PRD scope)
- **#34** — `wpa comment count` (moderation queue convenience; low priority)
- **#35** — `wpa term merge` (taxonomy cleanup with children handling + dry-run; medium priority)

### 2026-04-15: gh issue create wrong-repo incident

Filed the three follow-up issues via a parallel `gh issue create` batch. The first call was prefixed with `cd ~/Repos/cadentdev/wpa && gh issue create ... &`; the subsequent two were plain `gh issue create ... &`. In bash, `cd` only applies before the first `&`, so the two backgrounded calls ran in the default cwd (`~/.claude`) and `gh` defaulted to that repo's remote — `danielmiessler/Personal_AI_Infrastructure` upstream — filing #1070 and #1071 against PAI by mistake. Closed both upstream issues with an apology and re-filed correctly using explicit `-R cadentdev/wpa` on each call. **Captured in Phase 9 retro #2 above.**

### 2026-04-15: Phase 4 refactor caught a taxonomy-case routing bug

The `_resolve_endpoint` regex used `re.IGNORECASE`, so mixed-case input (`POST_TAG`, `Category`, `Genre`) passed validation but the case-sensitive `_TAXONOMY_ENDPOINTS` lookup fell through, routing to `/wp/v2/POST_TAG` (404). Fixed in commit `f71ca00` with 3 TDD tests (red → green confirmed). Would have shipped silently to any user passing mixed-case taxonomy slugs.

### 2026-04-15: Phase 8c live smoke test caught the WP REST API status asymmetry

First smoke-test run showed an empty result for `wpa comment list --post 11 --status approved` even when approved comments existed. Direct curl against the WP REST API confirmed it: `?status=approved` returns `[]`, `?status=approve` returns the data. Fixed in commit `658e0cf` with 3 TDD tests — normalize `approved → approve` at the `list_comments` boundary, accept both forms from the caller. **Captured in Phase 9 retro #4 above.**

### 2026-04-15: Ansible rollback playbook written from ad-hoc work

After doing the CT 118 rollback by hand via `ssh ... pct rollback 118 wpa_baseline` three times during Phase 8c iterations, extracted the pattern into `playbooks/on_demand/pve_ct_rollback.yml` in cadentdev/ansible. Tested live, filed as cadentdev/ansible#8 with full notes, opened PR #9. The playbook is better than a "design-first" version would have been because doing it by hand first exposed the important guards (snapshot-exists pre-flight, CT status polling, optional HTTP verify_url probe).

### 2026-04-15: Fixture image bumped from 1x1 to 256x256

Neil reported the Featured post image "didn't display" while browsing the rendered site. Diagnosis: the fixture was a valid 1×1 red PNG. Fit-for-purpose as an upload test, invisible to a human browser user. Bumped to a 256×256 RGB PNG with a red block and a white X across both diagonals — clearly a placeholder, visibly rendered. Generated with a pure-stdlib PNG writer (struct + zlib) so no new deps. 1.8 KB base64 inlined in the script. **Captured in Phase 9 retro #6 above.**

### 2026-04-15: Persistent + transient comment pattern

Neil's next browser-walk question was "does the smoke test add any comments?" — exposing that Section 5 created one comment and deleted it before exiting. Restructured to create two comments: a persistent one (approved immediately, left in place as a rendered-site artifact) and a transient one (walks the full state machine, force-deleted at end). Mid-run list now returns both, exercising multi-result listing. **Captured in Phase 9 retro #7 above.**
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
