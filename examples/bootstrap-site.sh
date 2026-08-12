#!/usr/bin/env bash
# examples/bootstrap-site.sh
#
# Bootstrap a WordPress site from code using only the `wpa` CLI.
#
# This script is a dual-purpose artifact:
#
#   1. A DEMO of how to stand up a WordPress site from code — a template
#      you can copy and modify to provision real sites for clients or
#      staging environments, using nothing but `wpa` CLI invocations.
#
#   2. A SMOKE TEST that exercises every user-facing wpa command we shipped
#      through v0.11.0 — user CRUD + role management, media upload, page
#      CRUD with media embedding, post CRUD with media embedding, comment
#      CRUD + moderation + counts, taxonomy term CRUD (categories and tags via
#      both the generic `wpa term` interface and the `wpa category` / `wpa
#      tag` aliases), plugin management, markdown-file content input, authored
#      publishing, site settings, nav menus, sidebars and classic widgets, and
#      the read-only introspection surface (taxonomies, post types, blocks,
#      themes, REST API discovery).
#
# The script is creation-only by design. It does NOT delete the user,
# posts, pages, or media items it creates. The intended reset pattern
# for a release-gate smoke test is to run this script against a Proxmox
# container (or other WordPress target) that you roll back to a baseline
# snapshot between runs — the script creates, the rollback resets.
#
# -----------------------------------------------------------------------------
# Requirements
# -----------------------------------------------------------------------------
#
#   - `wpa` installed and on PATH (`pip install wpa` or `pip install -e .`)
#   - A wpa site config for the target WordPress instance, created via
#     `wpa site add`. The Application Password used must have permission
#     to manage users, media, pages, and posts (normally an administrator
#     application password).
#   - The target site should be in a known baseline state (fresh WP install
#     or a state you control) so re-runs are reproducible.
#   - `base64` and standard POSIX text tools (`grep`, `awk`) — all present
#     on any Linux host that already has `wpa` installed.
#
# -----------------------------------------------------------------------------
# Signature prefix
# -----------------------------------------------------------------------------
#
# Everything created by this script is stamped with a caller-supplied
# prefix string. The prefix is used in usernames, titles, and visible
# content so that:
#
#   - Items are easy to identify and filter after the fact
#     (`wpa post list --search "${PREFIX}"`)
#   - Multiple runs against the same target with different prefixes
#     don't collide
#   - Cleanup after an ad-hoc run is trivial — search by prefix, pipe
#     IDs into delete
#
# The real protection against accidental production-targeting is the
# WordPress Application Password itself: you cannot use wpa against a
# site unless you have been issued credentials for it. The prefix is a
# bookkeeping convenience, not a safety mechanism.
#
# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------
#
#   ./bootstrap-site.sh --site <wpa-site-config> --prefix <signature>
#   ./bootstrap-site.sh -s ct118 -p wpa-demo
#
# Example:
#
#   ./bootstrap-site.sh --site ct118 --prefix demo-2026-04-14
#
# -----------------------------------------------------------------------------
# Exit codes
# -----------------------------------------------------------------------------
#
#   0   success — all commands completed, site bootstrapped
#   1   argument parsing or environment sanity check failed
#   2+  a `wpa` command failed (set -e halts on first failure)
#
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------

SITE=""
PREFIX=""

usage() {
    cat <<EOF
Usage: $0 --site <wpa-site-config> --prefix <signature>

Options:
  -s, --site    Name of the wpa site config (set up via 'wpa site add')
  -p, --prefix  Signature string stamped on all created items
  -h, --help    Show this help and exit

Example:
  $0 --site ct118 --prefix demo-2026-04-14
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--site)   SITE="$2";   shift 2 ;;
        -p|--prefix) PREFIX="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

[[ -z "$SITE"   ]] && { echo "Error: --site is required"   >&2; usage; }
[[ -z "$PREFIX" ]] && { echo "Error: --prefix is required" >&2; usage; }

# -----------------------------------------------------------------------------
# Sanity checks
# -----------------------------------------------------------------------------

command -v wpa >/dev/null 2>&1 || {
    echo "Error: wpa not found on PATH." >&2
    echo "Install with 'pip install wpa' or 'pip install -e .' from the wpa repo." >&2
    exit 1
}

# ⛔ VERSION ASSERTION — DO NOT REMOVE. This replaced a comment reading "We don't
# version-check ... will fail loudly on any missing subcommand via set -e".
# That reasoning was wrong in a way that yields a SILENT FALSE PASS:
#
#   Measured on flicky 2026-08-12 — `~/.local/bin/wpa` was **0.6.0** while the
#   repo venv held the 0.11.0 editable install. Running this script exactly as
#   its own usage line documents would have exercised a FIVE-RELEASE-OLD CLI,
#   and the result would have been recorded as a v0.11.0 release gate.
#
# "It'll fail loudly" does not hold either: an older wpa exits 2 with an argparse
# usage message, which reads like a flag typo rather than a version mismatch.
# A gate that the wrong binary can pass is not a gate.
#
# Run from a checkout with the venv first on PATH:
#   PATH="$PWD/.venv/bin:$PATH" ./examples/bootstrap-site.sh --site ct118 --prefix p
REQUIRED_WPA_VERSION="0.11.0"
ACTUAL_WPA_VERSION="$(wpa --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || true)"
if [[ "${ACTUAL_WPA_VERSION}" != "${REQUIRED_WPA_VERSION}" ]]; then
    echo "Error: this script targets the wpa ${REQUIRED_WPA_VERSION} command surface," >&2
    echo "       but the wpa on PATH reports '${ACTUAL_WPA_VERSION:-unknown}'." >&2
    echo "       Resolved binary: $(command -v wpa)" >&2
    echo "       Run from a checkout with the venv first on PATH." >&2
    exit 1
fi
echo "wpa ${ACTUAL_WPA_VERSION} — $(command -v wpa)"

# -----------------------------------------------------------------------------
# Helper: classify a failure as an ENVIRONMENT LIMIT rather than a wpa defect
# -----------------------------------------------------------------------------
#
# Some of the v0.10.0 surface is classic-theme-only (sidebars, classic widgets,
# nav menu locations) and some needs capabilities the App Password may not carry
# (manage_options, edit_theme_options). On a block theme those legitimately have
# nothing to return.
#
# ⛔ THE TRAP THIS AVOIDS: wrapping such calls in `|| true` would turn every
# genuine wpa bug in these sections into an "environment limitation" and produce
# a green gate over a broken CLI. So this helper branches THREE ways, not two:
#
#   rc = 0                      -> PASS, output shown
#   rc != 0 and 401/403         -> ENVIRONMENT (capability not granted), noted
#   rc != 0 and 404             -> ENVIRONMENT (route not registered), noted
#   rc != 0 and anything else   -> re-raised, so `set -e` halts the run
#
# An empty-but-successful listing is a PASS, not an environment limit — the
# command answered correctly, the answer was just "none".
ENV_LIMITS=()
soft_run() {
    local label="$1"; shift
    local output rc
    set +e
    output="$("$@" 2>&1)"
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
        echo "${output}"
        return 0
    fi
    if grep -qE 'WordPress API error (401|403)' <<<"${output}"; then
        echo "  [environment] ${label}: capability not granted to this App Password"
        ENV_LIMITS+=("${label}: capability not granted")
        return 0
    fi
    if grep -qE 'WordPress API error 404' <<<"${output}"; then
        echo "  [environment] ${label}: REST route not registered on this install"
        ENV_LIMITS+=("${label}: route not registered")
        return 0
    fi
    echo "${output}" >&2
    echo "Error: ${label} failed with rc=${rc} — this is a wpa defect, not an environment limit." >&2
    return "${rc}"
}

# -----------------------------------------------------------------------------
# Helper: extract an ID from wpa command output
# -----------------------------------------------------------------------------
#
# Several wpa subcommands print a line like "... ID: <n>" after a successful
# create. This helper reads the output from stdin and extracts the first
# numeric ID it finds. If no ID is found, it exits non-zero so `set -e`
# halts the run — that's the behavior we want for a smoke test.
#
# Usage:
#   OUTPUT=$(wpa post create ...)
#   ID=$(echo "$OUTPUT" | extract_id)

extract_id() {
    local id
    id=$(grep -oE 'ID:?\s*[0-9]+' | head -n1 | grep -oE '[0-9]+' || true)
    if [[ -z "$id" ]]; then
        echo "Error: could not parse ID from wpa output" >&2
        return 1
    fi
    echo "$id"
}

# -----------------------------------------------------------------------------
# Helper: run wpa, show its output, capture it, and extract the ID
# -----------------------------------------------------------------------------
#
# We want to (a) see what wpa said in real time, (b) parse the ID out of
# the output for later use. `tee` splits the stream: one copy to stderr
# so the operator sees the command output, one copy back to the caller
# for ID extraction.

run_and_capture() {
    local output
    output=$("$@" | tee /dev/stderr)
    echo "$output"
}

# -----------------------------------------------------------------------------
# Banner
# -----------------------------------------------------------------------------

echo "============================================================"
echo " wpa bootstrap-site"
echo "   Site:   ${SITE}"
echo "   Prefix: ${PREFIX}"
echo "============================================================"
echo

# =============================================================================
# 1. USER MANAGEMENT
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa user create    (existing, pre-v0.7.0)
#   - wpa user get       (NEW in v0.7.0)
#   - wpa user set-role  (NEW in v0.7.0)
#   - wpa user list      (existing, with --role filter)
#
# What this tests/demonstrates:
#
#   - Creating a WordPress user from the CLI with a supplied password
#   - Fetching a single user by ID to verify the record round-trips
#   - Promoting a user from subscriber to editor via the new set-role
#     shortcut (which is equivalent to `wpa user update <id> --role editor`
#     but matches the wp-cli `wp user set-role` convention)
#   - Listing users filtered by role to confirm the promotion took effect

echo "=== 1. User management ==="
echo

# Derive a unique username, email, and password from the caller's prefix.
# Using the prefix in all three means re-runs on a clean target are
# reproducible, and re-runs on a dirty target fail loudly on the
# duplicate-username error — which is the correct behavior for a smoke
# test (it tells you the baseline was not reset).
USER_USERNAME="${PREFIX}-author"
USER_EMAIL="${PREFIX}-author@example.test"
USER_PASSWORD="ChangeMe-${PREFIX}-$(date +%s)"

echo "Creating user ${USER_USERNAME}..."
USER_CREATE_OUT=$(printf '%s\n' "${USER_PASSWORD}" | wpa user create \
    --site "${SITE}" \
    --username "${USER_USERNAME}" \
    --email "${USER_EMAIL}" \
    --password-stdin \
    --role subscriber)
echo "$USER_CREATE_OUT"

# Parse the new user's ID. If wpa user create doesn't print "ID: <n>",
# fall back to looking the user up by username via wpa user list --ids.
USER_ID=$(echo "$USER_CREATE_OUT" | extract_id 2>/dev/null || true)
if [[ -z "$USER_ID" ]]; then
    echo "Create output did not contain an ID — looking up by username..."
    USER_ID=$(wpa user list --site "${SITE}" --search "${USER_USERNAME}" --ids | head -n1)
fi
[[ -z "$USER_ID" ]] && { echo "Error: could not resolve user ID after create" >&2; exit 1; }
echo "Created user ID=${USER_ID}"
echo

# Fetch the user back by ID — tests that wpa user get works end-to-end.
echo "Fetching user ${USER_ID} via 'wpa user get'..."
wpa user get "${USER_ID}" --site "${SITE}"
echo

# Promote the user to editor using the new set-role shortcut.
echo "Promoting user ${USER_ID} to editor via 'wpa user set-role'..."
wpa user set-role "${USER_ID}" editor --site "${SITE}"
echo

# List editors to confirm the promotion took effect.
echo "Listing users filtered by role=editor..."
wpa user list --site "${SITE}" --role editor --format table
echo

# =============================================================================
# 2. MEDIA LIBRARY
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa media import  (NEW in v0.7.0 — multipart upload of a local file)
#   - wpa media list    (NEW in v0.7.0 — with filters and output modifiers)
#   - wpa media get     (NEW in v0.7.0 — fetch a single media item by ID)
#
# What this tests/demonstrates:
#
#   - Uploading a local file to the WordPress media library via the REST
#     API's multipart upload path
#   - Attaching title, alt-text, caption, and description metadata at
#     upload time
#   - Retrieving a media item's source URL after upload so we can embed
#     it in subsequent posts and pages

echo "=== 2. Media library ==="
echo

# Generate two PNG fixture files in a temp directory. We embed a 256x256
# PNG as base64 so this script has no external fixture dependencies — any
# host that can run bash and base64 can run this script. The fixture is
# deliberately a recognizable "placeholder" (a red block with a white X
# marking both diagonals) so it's obvious when browsing the rendered site
# that the content was created by a smoke test, not a real upload. The
# base64 payload below is ~1.8 KB. Generated with a hand-rolled stdlib
# PNG writer (struct + zlib) so regenerating it needs no external tools.
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# A valid 256x256 RGB PNG: deep-red block (0xD02020) with 32px-wide white
# X across both diagonals. Compressed size ~1.4 KB binary, ~1.8 KB base64.
PNG_B64='iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAAFMUlEQVR42u3bW04bARQE0V4K+19NdkSSrygRCdh4iGfqWPWNNX2rJB5mrze+vr28AE/LrT7v9faXlXEN++8MQAO4hv33B6ABXMD+TwWgAZzd/s8GoAGc2v4HBKABnNf+xwSgAZzU/ocFoAGc0f5HBqABnM7+BwegAZzL/scHoAGcyP5DAtAAzmL/UQFoAKew/8AANIDnt//YADSAJ7f/ZwBHv4H74Wnt//H19zVvAzyh/b8C0ACC9v8WgAZQs//PADSAlP1vBKABdOx/OwANIGL/XwPQAAr2/ysADeDy9r8TgAZwbfvfD0ADuLD9HwpAA7iq/R8NQAO4pP03BKABXM/+2wLQAC5m/80BaABXsv+eADSAy9h/ZwAawGW02ZUeBuz/ugA0gAuosqs+GNj/FQFoAKfWY4WHBPuPDUADOKkSqz0w2H9UABrA6TRY+eERt/+QADTA/hOdfoZA+egzB8rnnlFQPvRMg/KJZyCUjzszoXzWGQvlg85kKJ9yhkP5iDMfyuebEVE+3EyJ8slmUJSPNbOifKYZF+UDzcQon2aGRvkoMzfK55jRUT7ETI/yCeYAKI8/Z0B59jkGyoPPSVCeeg6D8shzHvaX550jsb887Jwq24BJzxSAgxmzHoCzmbEegOMZsB6AE5quHoBDGq0egHOaqx6AoxqqHoDTmqgegAMbpx6AM5ulHoBjG6QegJOboh6AwxuhHoDzs78eQFkC9gugqwL7BdAVgv0C6GrBfgF05WC/ALqKsF8AXVHYL4CuLuwXQFca9gugqw77BdAViP0C6GrEfgF0ZWK/ALpKsV8A3QbYL4BuA+wXQLcB9gug2wD7BdBtgP0C6DbAfgF0G2C/ALoNsF8A3QbYL4BuA+wXQLcB9gug2wD7BdBtgP0C0AD7BaAB9gtAA+wXgAbYLwANsF8AGmC/ADTAfgFogP0C0AD7BaAB9gtAA+wXQLwBmwug24C1BdBtwM4C6DZgYQEIAALwLRAE4IdgCMCvQSEAfwiDAHwUAgLwYTgIwMehIQD/EAMB+JdICCBgvwYEULdfAwKo268BAdTt14AA6vZrQAB1+zUggBPY/2VvAQE8qf0aEEDdfg0IoG6/BgRQt18DAqjbrwEB1O3XgADq9mtAAHX7NSCAuv0aEEDdfg0IoG6/BgRQt18DAqjbrwEBkEkDAqCRBgRAIA0IoK6OBgRQl0YDAqjrogEB1EXRgADqimhAAHU5NCCAuhYaEEBdCA0IoK6CBgRQl0AD6QCc3wjdABzeFN0AnNwg3QAc2yzdAJzZON0AHNhE3QCc1lDdABzVXN0AnNNo3QAc0nTdAJzQgN0AHM+M3QCczZjdABzMpN0AnMqw3QAcybzdANhv5G4A7Dd1NwD2G7wbAPvN3g2A/cbvBsB+J+gGwH6H6AbAfg10A2C/BroBsF8D3QDYr4FuAOzXQDcA9mvgvx9rBkX5ZDMlyoebEVE+38yH8hFnOJRPOZOhfNAZC+WzzkwoH3cGQvnEMw3Kh55RUD73zIHy0WcIlE8/E6AswNiPcgNjP8oNjP0oNzD2o9zA2I9yA2M/yg2M/Sg3MPaj3MDYj3IDYz/KDYz9KDcw9qPcwNiPcgNjP8oNjP0oNzD2o9zA2I9yA2M/yg2M/Sg3MPaj3MDYj3IDYz/KDYz9KDcw9qPcwNiPcgNjP8oNjP0oNzD2o9zA2I9yA2M/yg2M/Sg3MPaj3MDYj3IDYz/KDYz9KDcw9qPcwNiPcgNjP8oNjP0oNzD2o9zA2I9yA2M/yg18B9POQ8HC/W35AAAAAElFTkSuQmCC'

echo "Writing two tiny PNG fixtures to ${TMPDIR}..."
echo "$PNG_B64" | base64 -d > "${TMPDIR}/${PREFIX}-hero.png"
echo "$PNG_B64" | base64 -d > "${TMPDIR}/${PREFIX}-thumb.png"
ls -l "${TMPDIR}"
echo

# Upload the first image with full metadata — exercises all the optional
# flags on wpa media import.
echo "Importing hero image..."
MEDIA_HERO_OUT=$(wpa media import "${TMPDIR}/${PREFIX}-hero.png" \
    --site "${SITE}" \
    --title "${PREFIX}: Hero image" \
    --alt-text "${PREFIX} demo hero image, 1x1 red PNG" \
    --caption "Generated by bootstrap-site.sh" \
    --description "Fixture image created by the wpa bootstrap-site demo script.")
echo "$MEDIA_HERO_OUT"
MEDIA_HERO_ID=$(echo "$MEDIA_HERO_OUT" | extract_id)
echo "Hero media ID=${MEDIA_HERO_ID}"
echo

# Upload the second image with only a title — exercises the minimal-args
# path through wpa media import.
echo "Importing thumbnail image..."
MEDIA_THUMB_OUT=$(wpa media import "${TMPDIR}/${PREFIX}-thumb.png" \
    --site "${SITE}" \
    --title "${PREFIX}: Thumbnail image")
echo "$MEDIA_THUMB_OUT"
MEDIA_THUMB_ID=$(echo "$MEDIA_THUMB_OUT" | extract_id)
echo "Thumbnail media ID=${MEDIA_THUMB_ID}"
echo

# List media filtered by type=image to confirm both uploads show up.
echo "Listing media items of type=image..."
wpa media list --site "${SITE}" --media-type image --per-page 20
echo

# Fetch the hero image by ID to grab its source_url so we can embed it
# in later content. `wpa media get` prints key: value lines; source_url
# is a plain string field we can pull out with grep + awk.
echo "Fetching hero media ${MEDIA_HERO_ID} to get its source_url..."
MEDIA_HERO_URL=$(wpa media get "${MEDIA_HERO_ID}" --site "${SITE}" \
    | grep '^source_url:' \
    | awk '{print $2}')
[[ -z "$MEDIA_HERO_URL" ]] && { echo "Error: could not resolve source_url for media ${MEDIA_HERO_ID}" >&2; exit 1; }
echo "Hero source URL: ${MEDIA_HERO_URL}"
echo

# =============================================================================
# 3. PAGES
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa page create   (existing, create from --title/--content flags)
#   - wpa page get      (existing)
#   - wpa page update   (existing)
#   - wpa page list     (existing, with filters)
#
# What this tests/demonstrates:
#
#   - Creating a page from CLI flags (not from a markdown file)
#   - Creating a page whose body embeds an uploaded media item via a
#     standard <img src="..."> tag referencing the media's source_url
#   - Updating an existing page's title
#   - Listing pages filtered by status

echo "=== 3. Pages ==="
echo

# Create an "About" page with plain HTML content.
echo "Creating About page..."
ABOUT_OUT=$(wpa page create \
    --site "${SITE}" \
    --title "${PREFIX}: About" \
    --content "<p>This site was bootstrapped from code by the <code>wpa</code> CLI using the <code>${PREFIX}</code> signature.</p>" \
    --status publish)
echo "$ABOUT_OUT"
ABOUT_ID=$(echo "$ABOUT_OUT" | extract_id)
echo "About page ID=${ABOUT_ID}"
echo

# Create a second page whose body references the hero media item. This
# demonstrates "incorporating images into pages" using nothing but the
# source_url we retrieved above.
echo "Creating Gallery page with embedded media..."
GALLERY_OUT=$(wpa page create \
    --site "${SITE}" \
    --title "${PREFIX}: Gallery" \
    --content "<p>Featured image:</p><p><img src=\"${MEDIA_HERO_URL}\" alt=\"${PREFIX} hero image\" /></p>" \
    --status publish)
echo "$GALLERY_OUT"
GALLERY_ID=$(echo "$GALLERY_OUT" | extract_id)
echo "Gallery page ID=${GALLERY_ID}"
echo

# Fetch one of the pages back by ID.
echo "Fetching Gallery page ${GALLERY_ID} via 'wpa page get'..."
wpa page get "${GALLERY_ID}" --site "${SITE}"
echo

# Update the About page's title — tests `wpa page update`.
echo "Updating About page title via 'wpa page update'..."
wpa page update "${ABOUT_ID}" \
    --site "${SITE}" \
    --title "${PREFIX}: About (updated)"
echo

# List published pages to confirm both show up.
echo "Listing pages with status=publish..."
wpa page list --site "${SITE}" --status publish
echo

# =============================================================================
# 4. POSTS
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa post create   (existing, create from --title/--content flags)
#   - wpa post get      (existing)
#   - wpa post update   (existing)
#   - wpa post list     (existing, with filters)
#
# What this tests/demonstrates:
#
#   - Creating a post from CLI flags
#   - Creating a post that embeds an uploaded media item
#   - Updating an existing post (status transition from draft to publish)
#   - Listing posts filtered by status

echo "=== 4. Posts ==="
echo

# Create a first post as a draft — exercises the default-draft behavior
# by being explicit about it.
echo "Creating Welcome post (draft)..."
WELCOME_OUT=$(wpa post create \
    --site "${SITE}" \
    --title "${PREFIX}: Welcome" \
    --content "<p>This post was created by the wpa bootstrap-site demo script with signature <code>${PREFIX}</code>.</p>" \
    --status draft)
echo "$WELCOME_OUT"
WELCOME_ID=$(echo "$WELCOME_OUT" | extract_id)
echo "Welcome post ID=${WELCOME_ID}"
echo

# Create a second post with an embedded image — exercises the same
# media-embed pattern we used for the Gallery page, but on a post.
echo "Creating Featured post with embedded media..."
FEATURED_OUT=$(wpa post create \
    --site "${SITE}" \
    --title "${PREFIX}: Featured post" \
    --content "<p>Here is our hero image:</p><p><img src=\"${MEDIA_HERO_URL}\" alt=\"${PREFIX} hero image\" /></p>" \
    --status publish)
echo "$FEATURED_OUT"
FEATURED_ID=$(echo "$FEATURED_OUT" | extract_id)
echo "Featured post ID=${FEATURED_ID}"
echo

# Fetch the Featured post back by ID.
echo "Fetching Featured post ${FEATURED_ID} via 'wpa post get'..."
wpa post get "${FEATURED_ID}" --site "${SITE}"
echo

# Transition the Welcome post from draft to publish via `wpa post update`.
echo "Publishing Welcome post via 'wpa post update'..."
wpa post update "${WELCOME_ID}" \
    --site "${SITE}" \
    --status publish
echo

# List published posts to confirm both show up.
echo "Listing posts with status=publish..."
wpa post list --site "${SITE}" --status publish
echo

# =============================================================================
# 5. COMMENTS  (v0.8.0)
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa comment create    (NEW in v0.8.0)
#   - wpa comment get       (NEW in v0.8.0)
#   - wpa comment list      (NEW in v0.8.0 — with filters and output modifiers)
#   - wpa comment update    (NEW in v0.8.0)
#   - wpa comment approve   (NEW in v0.8.0 — moderation shortcut)
#   - wpa comment unapprove (NEW in v0.8.0 — moderation shortcut)
#   - wpa comment spam      (NEW in v0.8.0 — moderation shortcut)
#   - wpa comment unspam    (NEW in v0.8.0 — moderation shortcut)
#   - wpa comment trash     (NEW in v0.8.0 — moderation shortcut)
#   - wpa comment delete    (NEW in v0.8.0 — with --force for permanent)
#
# What this tests/demonstrates:
#
#   - Creating TWO comments against the Featured post from Section 4:
#       (a) a PERSISTENT comment that is approved immediately and left
#           in place — shows up in the rendered Featured post page when
#           you browse the site, proves end-to-end comment rendering
#       (b) a TRANSIENT comment that walks the full moderation state
#           machine and is then trashed + force-deleted at the end of
#           the section, so it does not linger as smoke-test cruft
#   - Fetching a comment back to verify the create round-tripped
#   - Walking the moderation state machine (approve → unapprove →
#     spam → unspam → back to approved) and asserting each transition
#   - Updating comment content after create
#   - Filtering the comment list by status and by post — the list
#     step after the state walk should return BOTH comments in
#     `status: approved`, exercising multi-result listing

echo "=== 5. Comments ==="
echo

# -------- Persistent comment (left in place) --------
# This one stays. It gets created, approved immediately (WP comments
# from authors without a prior approved comment default to `hold`), and
# is left on the Featured post as a visible artifact. Running the script
# multiple times against a dirty target accumulates these — clean up by
# rolling the target back to a baseline snapshot, or by deleting the
# ID printed in the summary at the bottom of this script.
echo "Creating PERSISTENT comment on Featured post ${FEATURED_ID}..."
PERSIST_CREATE_OUT=$(wpa comment create \
    --site "${SITE}" \
    --post "${FEATURED_ID}" \
    --content "<p>Persistent smoke-test comment from <code>${PREFIX}</code>. Left in place as a rendered-site artifact.</p>" \
    --author-name "${PREFIX} Reader" \
    --author-email "${PREFIX}-reader@example.test")
echo "$PERSIST_CREATE_OUT"
PERSIST_COMMENT_ID=$(echo "$PERSIST_CREATE_OUT" | extract_id)
echo "Persistent comment ID=${PERSIST_COMMENT_ID}"
echo

echo "Approving persistent comment ${PERSIST_COMMENT_ID}..."
wpa comment approve "${PERSIST_COMMENT_ID}" --site "${SITE}"
echo

# -------- Transient comment (full state-machine walk, then deleted) --------
# This one is for exercising the moderation shortcuts and then gets
# cleaned up before the script exits. It does NOT leave an artifact
# behind — re-runs against a dirty target won't accumulate transient
# comments the way they accumulate persistent ones.
echo "Creating TRANSIENT comment on Featured post ${FEATURED_ID}..."
COMMENT_CREATE_OUT=$(wpa comment create \
    --site "${SITE}" \
    --post "${FEATURED_ID}" \
    --content "<p>Transient smoke-test comment from the <code>${PREFIX}</code> reviewer.</p>" \
    --author-name "${PREFIX} Reviewer" \
    --author-email "${PREFIX}-reviewer@example.test")
echo "$COMMENT_CREATE_OUT"
COMMENT_ID=$(echo "$COMMENT_CREATE_OUT" | extract_id)
echo "Transient comment ID=${COMMENT_ID}"
echo

# Fetch the comment back — tests `wpa comment get`.
echo "Fetching comment ${COMMENT_ID} via 'wpa comment get'..."
wpa comment get "${COMMENT_ID}" --site "${SITE}"
echo

# Walk the moderation state machine. Each call is a thin wrapper over a
# status update, but we want to make sure every shortcut is wired all the
# way through to the REST API.

echo "Holding comment (unapprove)..."
wpa comment unapprove "${COMMENT_ID}" --site "${SITE}"
echo

echo "Marking comment as spam..."
wpa comment spam "${COMMENT_ID}" --site "${SITE}"
echo

echo "Restoring from spam..."
wpa comment unspam "${COMMENT_ID}" --site "${SITE}"
echo

echo "Approving comment..."
wpa comment approve "${COMMENT_ID}" --site "${SITE}"
echo

# List with --status approved immediately after approve — confirms the
# moderation wrapper round-tripped to the REST API. This MUST run before
# the content update below; editing content can re-trigger WordPress
# moderation and transition the comment back out of `approved`. At this
# point BOTH comments (persistent + transient) should be in status
# `approved` and both should appear in the listing.
echo "Listing approved comments on Featured post ${FEATURED_ID}..."
wpa comment list --site "${SITE}" --post "${FEATURED_ID}" --status approved
echo

# Update the comment's content via `wpa comment update`.
echo "Updating comment content..."
wpa comment update "${COMMENT_ID}" \
    --site "${SITE}" \
    --content "<p>Updated by the ${PREFIX} smoke test at $(date -u +%FT%TZ).</p>"
echo

# After the content edit, re-list without any status filter. Note: the
# WordPress REST API defaults `status` to `approved` when the caller omits
# it, so `wpa comment list --post <id>` effectively means "approved on
# this post". If WordPress moved the comment back to `hold` after the
# edit (moderation hook re-run), this will show zero results — that's
# expected behavior, not a smoke-test failure. To see all statuses, pass
# each one explicitly: --status approved, --status hold, etc.
echo "Listing approved comments on Featured post ${FEATURED_ID} (post-edit)..."
wpa comment list --site "${SITE}" --post "${FEATURED_ID}" --status approved
echo

# Trash then force-delete. This is the one piece of smoke-test content
# we actively clean up so re-runs don't accumulate dead comments.
echo "Trashing comment ${COMMENT_ID}..."
wpa comment trash "${COMMENT_ID}" --site "${SITE}"
echo

echo "Permanently deleting comment ${COMMENT_ID}..."
wpa comment delete "${COMMENT_ID}" --site "${SITE}" --force
echo

# =============================================================================
# 6. TAXONOMY TERMS — CATEGORIES AND TAGS  (v0.8.0)
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa category create   (NEW in v0.8.0 — alias for 'term --taxonomy=category')
#   - wpa category list     (NEW in v0.8.0)
#   - wpa tag create        (NEW in v0.8.0 — alias for 'term --taxonomy=post_tag')
#   - wpa tag list          (NEW in v0.8.0)
#   - wpa term create       (NEW in v0.8.0 — generic taxonomy creator)
#   - wpa term list         (NEW in v0.8.0)
#   - wpa term get          (NEW in v0.8.0)
#   - wpa term update       (NEW in v0.8.0)
#   - wpa term delete       (NEW in v0.8.0 — always permanent; terms
#                           cannot be trashed in the REST API)
#
# What this tests/demonstrates:
#
#   - Creating a category via the `wpa category` alias (pre-sets
#     --taxonomy=category so the user doesn't have to)
#   - Creating a tag via the `wpa tag` alias (pre-sets --taxonomy=post_tag)
#   - Creating a second category via the generic `wpa term --taxonomy=category`
#     form to prove the alias and the generic path hit the same endpoint
#   - Listing categories and tags separately
#   - Updating a term's description after create
#   - Deleting a term — which is always a permanent delete, not a trash

# Comment counts per moderation status (NEW in v0.8.2). Runs last in this
# section so the tally reflects everything the section did: the persistent
# approved comment survives, the transient one was force-deleted.
echo "Counting comments per moderation status..."
wpa comment count --site "${SITE}"
echo

echo "=== 6. Taxonomy terms (categories and tags) ==="
echo

# Create a category via the alias. The prefix keeps runs distinct.
echo "Creating category via 'wpa category create'..."
CAT_CREATE_OUT=$(wpa category create \
    --site "${SITE}" \
    --name "${PREFIX} Alias Category" \
    --description "Created via the wpa category alias in the bootstrap smoke test.")
echo "$CAT_CREATE_OUT"
CAT_ID=$(echo "$CAT_CREATE_OUT" | extract_id)
echo "Category ID=${CAT_ID}"
echo

# Create a second category via the generic term interface — both should
# hit /wp/v2/categories.
echo "Creating second category via 'wpa term create --taxonomy=category'..."
CAT2_CREATE_OUT=$(wpa term create \
    --site "${SITE}" \
    --taxonomy category \
    --name "${PREFIX} Generic Category" \
    --description "Created via the wpa term generic interface.")
echo "$CAT2_CREATE_OUT"
CAT2_ID=$(echo "$CAT2_CREATE_OUT" | extract_id)
echo "Category ID=${CAT2_ID}"
echo

# Create a tag via the alias.
echo "Creating tag via 'wpa tag create'..."
TAG_CREATE_OUT=$(wpa tag create \
    --site "${SITE}" \
    --name "${PREFIX}-alias-tag" \
    --description "Created via the wpa tag alias.")
echo "$TAG_CREATE_OUT"
TAG_ID=$(echo "$TAG_CREATE_OUT" | extract_id)
echo "Tag ID=${TAG_ID}"
echo

# Create a second tag via the generic term interface with post_tag.
echo "Creating second tag via 'wpa term create --taxonomy=post_tag'..."
TAG2_CREATE_OUT=$(wpa term create \
    --site "${SITE}" \
    --taxonomy post_tag \
    --name "${PREFIX}-generic-tag")
echo "$TAG2_CREATE_OUT"
TAG2_ID=$(echo "$TAG2_CREATE_OUT" | extract_id)
echo "Tag ID=${TAG2_ID}"
echo

# Fetch the alias category back — tests `wpa term get` with the --taxonomy
# flag. We use the generic form here to prove term get works across
# taxonomies (the alias also works, but we already tested alias-create).
echo "Fetching category ${CAT_ID} via 'wpa term get --taxonomy=category'..."
wpa term get "${CAT_ID}" --site "${SITE}" --taxonomy category
echo

# Update the alias category's description.
echo "Updating category ${CAT_ID} description via 'wpa category update'..."
wpa category update "${CAT_ID}" \
    --site "${SITE}" \
    --description "Updated by the ${PREFIX} smoke test."
echo

# List categories (via alias) and tags (via alias) to confirm the new items
# show up.
echo "Listing categories via 'wpa category list'..."
wpa category list --site "${SITE}" --search "${PREFIX}"
echo

echo "Listing tags via 'wpa tag list'..."
wpa tag list --site "${SITE}" --search "${PREFIX}"
echo

# Clean up one of each (generic category + generic tag) to prove that
# `wpa term delete` hits the correct endpoint and always force-deletes.
# We leave the alias-created category and tag in place so the summary
# table and the WordPress admin reflect a non-empty smoke-test footprint,
# consistent with the "the script creates and the rollback resets"
# baseline model.

echo "Deleting generic category ${CAT2_ID} (always permanent)..."
wpa term delete "${CAT2_ID}" --site "${SITE}" --taxonomy category
echo

echo "Deleting generic tag ${TAG2_ID} (always permanent)..."
wpa term delete "${TAG2_ID}" --site "${SITE}" --taxonomy post_tag
echo

# =============================================================================
# 7. PLUGINS  (v0.10.0)
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa plugin list        (NEW in v0.10.0 — with --status filter)
#   - wpa plugin get         (NEW in v0.10.0)
#   - wpa plugin deactivate  (NEW in v0.10.0)
#   - wpa plugin activate    (NEW in v0.10.0)
#
# The round-trip (list → deactivate → activate → confirm) is idempotent:
# it targets a plugin that is known-installed and known-active on the
# rollback baseline, and ends with the plugin active again. Requires the
# authenticated user to have the activate_plugins capability (admin).
#
# SMOKE_PLUGIN defaults to Akismet, which ships with stock WordPress.
# Override for targets with a different baseline:
#   SMOKE_PLUGIN="wordfence/wordfence" ./bootstrap-site.sh ...
SMOKE_PLUGIN="${SMOKE_PLUGIN:-akismet/akismet}"

echo "=== 7. Plugins ==="
echo

echo "Listing installed plugins..."
wpa plugin list --site "${SITE}"
echo

echo "Fetching plugin ${SMOKE_PLUGIN}..."
wpa plugin get "${SMOKE_PLUGIN}" --site "${SITE}"
echo

echo "Deactivating ${SMOKE_PLUGIN}..."
wpa plugin deactivate "${SMOKE_PLUGIN}" --site "${SITE}"
echo

echo "Re-activating ${SMOKE_PLUGIN}..."
wpa plugin activate "${SMOKE_PLUGIN}" --site "${SITE}"
echo

echo "Confirming via active-only listing (should include ${SMOKE_PLUGIN})..."
wpa plugin list --site "${SITE}" --status active
echo

# =============================================================================
# 8. MARKDOWN FILE INPUT AND AUTHORED PUBLISHING
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa post create --file   (NEW in v0.8.2 — markdown + YAML frontmatter)
#   - wpa publish --author     (NEW in v0.9.0 — author override)
#
# What this tests/demonstrates:
#
#   - Authoring content as a markdown file rather than an inline --content
#     string, which is the realistic workflow for anything longer than a
#     sentence and the one the frontmatter parser exists to serve
#   - Frontmatter supplying the title, so --title is NOT passed on the CLI
#   - Attributing a published page to a specific user via --author, rather
#     than to whoever owns the Application Password
#
# ⚠️ --author takes a user ID, not a username. We reuse USER_ID created in
# section 1, which is the only non-admin user this run knows about.

echo "=== 8. Markdown file input and authored publishing ==="
echo

MD_POST_FILE="$(mktemp -t "${PREFIX}-post-XXXXXX.md")"
MD_PAGE_FILE="$(mktemp -t "${PREFIX}-page-XXXXXX.md")"

# Frontmatter carries the title — the CLI deliberately does not pass --title,
# so a regression in frontmatter parsing surfaces as a missing/blank title
# rather than being masked by a CLI-supplied one.
cat > "${MD_POST_FILE}" <<EOF
---
title: "${PREFIX}: Markdown post"
status: publish
---

# ${PREFIX}: Markdown post

This post was created from a **markdown file** via \`wpa post create --file\`,
not from an inline \`--content\` string.

- Frontmatter supplied the title
- The body was converted from markdown to HTML by wpa
EOF

cat > "${MD_PAGE_FILE}" <<EOF
---
title: "${PREFIX}: Authored page"
status: publish
---

# ${PREFIX}: Authored page

This page was published with \`wpa publish --author\`, attributing it to a
user other than the owner of the Application Password.
EOF

echo "Creating a post from a markdown file (title comes from frontmatter)..."
MD_POST_OUT=$(wpa post create --file "${MD_POST_FILE}" --site "${SITE}")
echo "${MD_POST_OUT}"
MD_POST_ID=$(echo "${MD_POST_OUT}" | extract_id)
echo "  -> post ID ${MD_POST_ID}"
echo

echo "Verifying the frontmatter title round-tripped..."
wpa post get "${MD_POST_ID}" --site "${SITE}"
echo

echo "Publishing a page attributed to user ${USER_ID} via 'wpa publish --author'..."
MD_PAGE_OUT=$(wpa publish "${MD_PAGE_FILE}" --author "${USER_ID}" --site "${SITE}")
echo "${MD_PAGE_OUT}"
MD_PAGE_ID=$(echo "${MD_PAGE_OUT}" | extract_id)
echo "  -> page ID ${MD_PAGE_ID}"
echo

echo "Confirming the author stuck (expect author=${USER_ID}, not the API-password owner)..."
wpa page get "${MD_PAGE_ID}" --site "${SITE}"
echo

rm -f "${MD_POST_FILE}" "${MD_PAGE_FILE}"

# =============================================================================
# 9. SITE SETTINGS
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa option list    (NEW in v0.10.0)
#   - wpa option get     (NEW in v0.10.0)
#   - wpa option update  (NEW in v0.10.0)
#
# What this tests/demonstrates:
#
#   - Reading and writing WordPress settings through the REST API
#
# ⚠️ REGISTERED SETTINGS ONLY. The REST settings endpoint exposes the settings
# core registers (title, description, timezone, posts_per_page, ...) — not the
# whole wp_options table. Asking for an unregistered name is a 404 BY DESIGN and
# must not be read as a wpa defect. We use `description` (the site tagline)
# because it is registered, harmless, and visibly wrong if it fails to write.
# Requires manage_options.

echo "=== 9. Site settings ==="
echo

echo "Listing registered settings..."
soft_run "option list" wpa option list --site "${SITE}"
echo

echo "Reading the current tagline..."
soft_run "option get description" wpa option get description --site "${SITE}"
echo

echo "Setting the tagline to a prefixed value..."
soft_run "option update description" \
    wpa option update description "${PREFIX}: bootstrapped tagline" --site "${SITE}"
echo

echo "Reading it back to prove the write landed..."
soft_run "option get description (readback)" wpa option get description --site "${SITE}"
echo

# =============================================================================
# 10. NAV MENUS
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa menu create         (NEW in v0.10.0)
#   - wpa menu get            (NEW in v0.10.0)
#   - wpa menu list           (NEW in v0.10.0)
#   - wpa menu item add       (NEW in v0.10.0)
#   - wpa menu item list      (NEW in v0.10.0)
#   - wpa menu location list  (NEW in v0.10.0)
#
# What this tests/demonstrates:
#
#   - Creating a nav menu and hanging both a custom link and a real page off it
#
# ⚠️ MENUS OUTLIVE CLASSIC THEMES. Nav menus are the `nav_menu` taxonomy, which
# core registers regardless of the active theme — so create/add works on a block
# theme even though the theme will never render the result. Menu LOCATIONS are
# theme-declared, so `menu location list` legitimately returns nothing under a
# block theme. Empty there is a PASS, not a failure.
#
# ⚠️ ARGUMENT SHAPE DIFFERS BETWEEN THE TWO: `menu item add` takes the menu as a
# POSITIONAL, `menu item list` takes it as `--menu`. Not a bug, but easy to trip
# over — see the note filed against the repo.

echo "=== 10. Nav menus ==="
echo

echo "Creating a nav menu..."
MENU_OUT=$(wpa menu create --name "${PREFIX} Main Menu" --site "${SITE}")
echo "${MENU_OUT}"
MENU_ID=$(echo "${MENU_OUT}" | extract_id)
echo "  -> menu ID ${MENU_ID}"
echo

echo "Fetching the menu back..."
wpa menu get "${MENU_ID}" --site "${SITE}"
echo

echo "Adding a custom link item (menu ID is POSITIONAL here)..."
wpa menu item add "${MENU_ID}" \
    --title "${PREFIX}: External" \
    --url "https://example.com/${PREFIX}" \
    --site "${SITE}"
echo

echo "Adding an item pointing at the About page created in section 3..."
wpa menu item add "${MENU_ID}" \
    --title "${PREFIX}: About" \
    --object page \
    --object-id "${ABOUT_ID}" \
    --site "${SITE}"
echo

echo "Listing the menu's items (menu ID is a FLAG here)..."
wpa menu item list --menu "${MENU_ID}" --site "${SITE}"
echo

echo "Listing all menus..."
wpa menu list --site "${SITE}"
echo

echo "Listing theme-declared menu locations (empty under a block theme)..."
wpa menu location list --site "${SITE}"
echo

# =============================================================================
# 11. SIDEBARS AND CLASSIC WIDGETS
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa sidebar list  (NEW in v0.10.0)
#   - wpa widget list   (NEW in v0.10.0)
#   - wpa widget get    (NEW in v0.10.0)
#
# What this tests/demonstrates:
#
#   - Enumerating registered sidebars and the widgets sitting in them
#
# ⚠️ READ-ONLY ON PURPOSE. widget update/deactivate/delete exist but are NOT
# exercised here: under a block theme the only sidebar is `wp_inactive_widgets`,
# the holding pen, so a "move" has nowhere to move to and a delete would destroy
# state the rollback is meant to define. Read-only keeps this section honest on
# both theme styles.
#
# ⚠️ A BLOCK THEME REGISTERS NO SIDEBARS. An empty listing here is the CORRECT
# answer, not a failure — which is exactly why these calls report what they got
# rather than asserting a non-empty result.

echo "=== 11. Sidebars and classic widgets ==="
echo

echo "Listing registered sidebars..."
soft_run "sidebar list" wpa sidebar list --site "${SITE}"
echo

echo "Listing widgets..."
soft_run "widget list" wpa widget list --site "${SITE}"
echo

# Pick the first widget ID, if any exist, and fetch it. Under a block theme the
# inactive-widgets pen usually holds a few `block-N` widgets from core defaults.
# See the note in section 12: the `grep -v '^Warning:'` works around
# cadentdev/wpa#81, where the LAN-HTTP warning lands on stdout. Remove it once
# that issue is fixed.
FIRST_WIDGET_ID=$(wpa widget list --site "${SITE}" --field id 2>/dev/null \
    | grep -v '^Warning:' | head -n1 | tr -d '[:space:]' || true)

if [[ -n "${FIRST_WIDGET_ID}" ]]; then
    echo "Fetching widget '${FIRST_WIDGET_ID}'..."
    soft_run "widget get" wpa widget get "${FIRST_WIDGET_ID}" --site "${SITE}"
else
    echo "  [environment] no widgets registered on this install — nothing to fetch"
    ENV_LIMITS+=("widget get: no widgets registered")
fi
echo

# =============================================================================
# 12. INTROSPECTION AND DISCOVERY
# =============================================================================
# Exercises the following wpa subcommands:
#
#   - wpa taxonomy list   (NEW in v0.11.0)
#   - wpa taxonomy get    (NEW in v0.11.0)
#   - wpa post-type list  (NEW in v0.11.0)
#   - wpa post-type get   (NEW in v0.11.0)
#   - wpa block list      (NEW in v0.11.0)
#   - wpa block get       (NEW in v0.11.0)
#   - wpa theme list      (NEW in v0.11.0)
#   - wpa theme get       (NEW in v0.11.0)
#   - wpa api discover    (NEW in v0.11.0)
#
# What this tests/demonstrates:
#
#   - Asking a site what it actually supports before acting on it, which is the
#     whole point of the v0.11.0 surface: these are the commands you run FIRST
#     against an unfamiliar install
#
# All read-only. The fixed arguments below (`category`, `page`, `core/paragraph`)
# are core-guaranteed on any WordPress, so a failure here is a wpa defect rather
# than a property of the install. The theme argument is resolved from the live
# listing instead, since which theme is active varies by target.

echo "=== 12. Introspection and discovery ==="
echo

echo "Listing registered taxonomies..."
wpa taxonomy list --site "${SITE}"
echo

echo "Fetching the 'category' taxonomy (core-guaranteed)..."
wpa taxonomy get category --site "${SITE}"
echo

echo "Listing registered post types..."
wpa post-type list --site "${SITE}"
echo

echo "Fetching the 'page' post type (core-guaranteed)..."
wpa post-type get page --site "${SITE}"
echo

echo "Listing registered block types..."
wpa block list --site "${SITE}"
echo

echo "Fetching the 'core/paragraph' block (core-guaranteed)..."
wpa block get core/paragraph --site "${SITE}"
echo

echo "Listing installed themes..."
wpa theme list --site "${SITE}"
echo

# Resolve the ACTIVE theme from the listing rather than hardcoding a stylesheet:
# the target's theme is a property of the install, not of wpa.
#
# ⛔ DO NOT PARSE THE TABLE FORMAT WITH awk POSITIONALS. The first attempt used
# `awk '$3 == "active"'`, which broke on the very first run: the `name` column
# holds "Twenty Twenty-Five", so the space inside the value shifts every later
# field and $3 is "Twenty-Five", never "active". Table output is for humans —
# any value containing a space silently derails column-position parsing.
#
# ⚠️ AND DO NOT USE `--format json` HERE EITHER, for now. On an http:// LAN site
# wpa prints its "Using HTTP on a private/LAN address" warning to STDOUT, so the
# JSON does not parse — cadentdev/wpa#81. `--field` is contaminated the same way.
# The grep below drops that line, which keeps this working both before and after
# that issue is fixed; delete the filter once #81 has landed.
ACTIVE_THEME=$(wpa theme list --site "${SITE}" --status active --field stylesheet 2>/dev/null \
    | grep -v '^Warning:' | head -n1 | tr -d '[:space:]' || true)
if [[ -n "${ACTIVE_THEME}" ]]; then
    echo "Fetching the active theme '${ACTIVE_THEME}'..."
    wpa theme get "${ACTIVE_THEME}" --site "${SITE}"
else
    echo "Error: could not resolve an active theme via" >&2
    echo "       'wpa theme list --status active --field stylesheet'." >&2
    echo "       Every WordPress install has exactly one active theme, so this is" >&2
    echo "       a wpa defect in --status/--field, not an environment limit." >&2
    exit 1
fi
echo

echo "Enumerating the REST API surface..."
wpa api discover --site "${SITE}"
echo

# =============================================================================
# 13. SUMMARY
# =============================================================================

echo "============================================================"
echo " Bootstrap complete"
echo "============================================================"
echo
echo "Created on site '${SITE}' with signature '${PREFIX}':"
echo
# Use printf with fixed-width ID column (%-6s) so summary stays aligned
# regardless of whether IDs are 1, 2, 3, or 4 digits. Titles are left-
# aligned and free-form.
printf "  %-10s ID=%-6s %s\n" "User"     "${USER_ID}"        "username=${USER_USERNAME} (editor)"
printf "  %-10s ID=%-6s %s\n" "Media"    "${MEDIA_HERO_ID}"  "title=${PREFIX}: Hero image"
printf "  %-10s ID=%-6s %s\n" "Media"    "${MEDIA_THUMB_ID}" "title=${PREFIX}: Thumbnail image"
printf "  %-10s ID=%-6s %s\n" "Page"     "${ABOUT_ID}"       "title=${PREFIX}: About (updated)"
printf "  %-10s ID=%-6s %s\n" "Page"     "${GALLERY_ID}"     "title=${PREFIX}: Gallery"
printf "  %-10s ID=%-6s %s\n" "Post"     "${WELCOME_ID}"     "title=${PREFIX}: Welcome"
printf "  %-10s ID=%-6s %s\n" "Post"     "${FEATURED_ID}"    "title=${PREFIX}: Featured post"
printf "  %-10s ID=%-6s %s\n" "Category" "${CAT_ID}"            "name=${PREFIX} Alias Category (updated)"
printf "  %-10s ID=%-6s %s\n" "Tag"      "${TAG_ID}"            "name=${PREFIX}-alias-tag"
printf "  %-10s ID=%-6s %s\n" "Comment"  "${PERSIST_COMMENT_ID}" "on Featured post (approved, persistent)"
printf "  %-10s ID=%-6s %s\n" "Post"     "${MD_POST_ID}"      "title=${PREFIX}: Markdown post (from --file)"
printf "  %-10s ID=%-6s %s\n" "Page"     "${MD_PAGE_ID}"      "title=${PREFIX}: Authored page (author=${USER_ID})"
printf "  %-10s ID=%-6s %s\n" "Menu"     "${MENU_ID}"         "name=${PREFIX} Main Menu (2 items)"
echo
echo "Site settings changed (reset by rolling the target back to baseline):"
echo
printf "  %-10s %s\n" "Tagline" "${PREFIX}: bootstrapped tagline"
echo

# Environment limits are reported SEPARATELY from failures. A limit means the
# command answered correctly and the answer was "this install has none of that"
# — a block theme with no sidebars, say. Anything that actually broke would have
# halted the run long before here, via set -e.
if [[ ${#ENV_LIMITS[@]} -gt 0 ]]; then
    echo "Environment limits observed (NOT failures — do not file these as bugs):"
    echo
    for limit in "${ENV_LIMITS[@]}"; do
        printf "  - %s\n" "${limit}"
    done
    echo
fi

echo "Created and then deleted during the run (v0.8.0 surface):"
echo
printf "  %-10s          %s\n" "Comment"  "transient, walked state machine — trashed then force-deleted"
printf "  %-10s          %s\n" "Category" "${PREFIX} Generic Category — force-deleted"
printf "  %-10s          %s\n" "Tag"      "${PREFIX}-generic-tag — force-deleted"
echo
echo "To clean up manually (the bootstrap script leaves the items above in place):"
echo
# Same %-6s trick for the cleanup commands so the --site flag lines up.
printf "  wpa comment  delete %-6s --site %s --force\n"    "${PERSIST_COMMENT_ID}" "${SITE}"
printf "  wpa post     delete %-6s --site %s --force\n"    "${WELCOME_ID}"         "${SITE}"
printf "  wpa post     delete %-6s --site %s --force\n"    "${FEATURED_ID}"        "${SITE}"
printf "  wpa page     delete %-6s --site %s --force\n"    "${ABOUT_ID}"           "${SITE}"
printf "  wpa page     delete %-6s --site %s --force\n"    "${GALLERY_ID}"         "${SITE}"
printf "  wpa media    delete %-6s --site %s --force\n"    "${MEDIA_HERO_ID}"      "${SITE}"
printf "  wpa media    delete %-6s --site %s --force\n"    "${MEDIA_THUMB_ID}"     "${SITE}"
printf "  wpa category delete %-6s --site %s\n"            "${CAT_ID}"             "${SITE}"
printf "  wpa tag      delete %-6s --site %s\n"            "${TAG_ID}"             "${SITE}"
printf "  wpa user     delete %-6s --site %s --reassign 1\n" "${USER_ID}"          "${SITE}"
echo
echo "Or, for a release-gate smoke test: roll back the target container"
echo "to its baseline snapshot (e.g. via an ansible playbook that runs"
echo "'pct rollback <ctid> <snapshot>' on the Proxmox host)."
echo
