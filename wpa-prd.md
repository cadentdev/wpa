# WPA — Product Requirements Document

**Product:** WPA (WordPress Automation)
**Version:** PRD v1.0
**Date:** 2026-03-21
**Author:** Neil Johnson, Cadent Creative
**Current release:** v0.5.1
**Repository:** [github.com/cadentdev/wpa](https://github.com/cadentdev/wpa)
**PyPI:** [pypi.org/project/wpa](https://pypi.org/project/wpa/)
**License:** MIT

---

## Table of contents

1. [Vision and purpose](#1-vision-and-purpose)
2. [Why WPA exists](#2-why-wpa-exists)
3. [What WPA is not](#3-what-wpa-is-not)
4. [Design principles](#4-design-principles)
5. [Architecture](#5-architecture)
6. [Command structure](#6-command-structure)
7. [Implementation roadmap](#7-implementation-roadmap)
8. [Reference documents](#8-reference-documents)

---

## 1. Vision and purpose

WPA is a Python command-line tool that provides a clean, intuitive interface for managing WordPress sites through the WordPress REST API. It gives developers, site administrators, and automated systems the ability to create, read, update, and delete WordPress content from any machine with Python installed — no server access, no PHP, no WordPress installation on the client side.

The goal is straightforward: bring the convenience of command-line WordPress management to anyone who can reach a WordPress site over HTTPS, with a command structure that feels natural to both WordPress veterans and newcomers.

WPA addresses a clear gap in the WordPress tooling ecosystem. Despite dozens of Python libraries wrapping the WordPress REST API, none provides a command-line interface. Despite wp-cli's dominance as the standard WordPress CLI tool, it requires direct server access and PHP execution — making it unavailable in a growing number of real-world scenarios. WPA fills the space between these two worlds: a CLI tool that speaks REST API, usable from anywhere, by anyone or anything that can run Python.

---

## 2. Why WPA exists

### 2.1 Fine-grained access control by design

wp-cli operates by bootstrapping WordPress's PHP environment directly. It runs with whatever permissions the server's PHP process has — which typically means unrestricted access to the filesystem, database, and every WordPress function. There is no capability boundary; wp-cli can do anything WordPress itself can do.

WPA takes a fundamentally different approach. Every operation is authenticated via a WordPress Application Password tied to a specific user account. That user account has a specific role (Administrator, Editor, Author, Contributor, Subscriber) with specific capabilities. An Author can create and edit their own posts but cannot delete others' posts or manage users. An Editor can manage all content but cannot install plugins or change site settings.

This isn't a limitation — it's a feature. Access control is enforced by WordPress itself at the API layer. WPA cannot circumvent it, and neither can anything using WPA. The blast radius of any operation is bounded by the authenticated user's role, exactly as WordPress intends.

### 2.2 Zero client-side dependencies

wp-cli requires PHP (7.2.24+), a local WordPress installation or SSH access to one, and the wp-cli binary itself. This means it cannot run on machines without PHP, cannot operate remotely without SSH, and cannot be used in environments where installing PHP is impractical or prohibited.

WPA requires Python (3.9+) and nothing else. There is no PHP dependency, no WordPress installation needed on the client, no server access of any kind. The only runtime dependencies are Python standard library modules plus `requests` (HTTP), `python-frontmatter` (markdown parsing), `markdown` (conversion), and `python-dotenv` (config). These are lightweight, well-maintained, and universally available.

This makes WPA usable in environments where wp-cli cannot run: CI/CD pipelines that don't have PHP, developer workstations that don't need PHP for their primary work, containerized build systems, cloud functions, Chromebooks, and any machine where `pip install wpa` is all you need.

### 2.3 Safe tool use by agentic AI systems

This is the forward-looking case that motivated WPA's creation and will drive its growth.

AI coding agents like Claude Code operate by executing shell commands on behalf of a user. When an agent needs to interact with a WordPress site, the available options today are poor: give the agent SSH access and let it run wp-cli (granting unrestricted server access), or have the agent write and execute Python scripts against a REST API library (slow, error-prone, no command-line composability).

WPA provides a third path that is purpose-built for this use case. An agent can run `wpa post list --site myblog --json` the same way it would run `git status` or `ls -la` — as a simple shell command that returns structured data. The security model is inherently right for agent use:

- **Principle of least privilege.** Create a dedicated WordPress user with only the capabilities the agent needs. Issue an Application Password for that user. The agent physically cannot exceed those permissions — not because of prompt engineering or safety rails, but because the WordPress REST API enforces it at the server.
- **Auditable operations.** Every action the agent takes is an HTTP request to a known endpoint. These requests appear in web server logs, can be monitored by WordPress audit plugins, and can be rate-limited by standard web infrastructure. There is no opaque "the agent ran some PHP" — every operation is visible and traceable.
- **Revocable credentials.** Application Passwords can be revoked instantly from the WordPress admin panel. If an agent's credentials are compromised or the agent misbehaves, access is cut off with a single click. No server access is needed to revoke access.
- **Composable with other CLI tools.** Because WPA returns structured output (JSON with `--json`, human-readable tables by default), agents can pipe `wpa` output to other tools, parse it programmatically, and build multi-step workflows without writing custom integration code.

### 2.4 Remote operation by default

wp-cli is fundamentally a local tool. It bootstraps PHP from the server's filesystem and operates on the WordPress installation in the current directory. To manage a remote site, you need SSH access and must run wp-cli on the server.

WPA is inherently remote. It talks to any WordPress site over HTTPS from anywhere. The site being managed and the machine running WPA can be on different continents. This model maps naturally to modern development workflows: managing a production site from a local development machine, running content updates from a CI pipeline, or having an AI agent manage multiple client sites from a single environment.

WPA's multi-site configuration system (`wpa site add`, `wpa site list`, `~/.config/wpa/<site-name>/.env`) is designed around this reality. One WPA installation manages any number of WordPress sites, each with its own URL, credentials, and configuration. wp-cli has no equivalent — it can only operate on one WordPress installation at a time.

### 2.5 HTTPS-enforced credential security

WPA enforces HTTPS for all public-facing WordPress URLs. Credentials are always encrypted in transit. HTTP is permitted only for RFC 1918 private addresses and localhost (for local development and home lab use), and even then WPA prints an explicit warning that credentials are not encrypted.

Credentials are stored in XDG-compliant config files (`~/.config/wpa/<site-name>/.env`) with 600 permissions, outside any project repository. Password input during setup uses `getpass` for hidden entry. Site names are validated to prevent path traversal.

This security model is enforced at the tool level, not left to user discipline. WPA will not send credentials over an unencrypted connection to a public address, regardless of what the user asks for.

### 2.6 Auditable, loggable, monitorable operations

Every WPA operation is an HTTP request to a WordPress REST API endpoint. These requests flow through the same web infrastructure as any other HTTP traffic: web server access logs, reverse proxies, CDN layers, WordPress security plugins, and application-level audit logging.

This means operations performed by WPA (including operations performed by AI agents using WPA) are visible to the same monitoring and security tooling that watches over the WordPress site itself. There is no separate audit trail to configure — WPA operations appear alongside browser-based admin actions in any logging system that captures HTTP requests.

wp-cli operations, by contrast, happen inside PHP execution and are largely invisible to web-layer monitoring. They do not generate HTTP requests, do not appear in web server logs, and require separate WordPress-level hooks to audit.

### 2.7 Predictable JSON output for automation

The WordPress REST API returns JSON natively. When WPA adds `--json` output formatting, it passes through what the API already returns — no serialization conversion, no format ambiguity. This makes WPA output directly consumable by `jq`, Python scripts, other CLI tools, and AI agents without parsing human-readable table output.

wp-cli supports JSON output via `--format=json`, but the output is serialized from PHP objects — a conversion step that can introduce inconsistencies with the REST API's native JSON representation. WPA's output is the REST API's output, processed only for display formatting.

---

## 3. What WPA is not

**WPA is not a replacement for wp-cli.** wp-cli is an essential tool with capabilities that WPA cannot and will not replicate. wp-cli can install and update WordPress core, manage the database directly, run search-replace operations across all tables, install and update plugins and themes via filesystem operations, execute arbitrary PHP, scaffold code, manage WP-Cron, and perform dozens of other operations that require direct server access.

WPA covers the subset of WordPress management that the REST API exposes — primarily content management (posts, pages, media, comments), user management, taxonomy and term management, plugin listing and activation, menu management, widget management, and site settings. This is roughly 34% of wp-cli's command surface area, but it is the 34% that matters most for content workflows and AI-assisted site management.

The correct mental model is: **wp-cli is a server-side power tool; WPA is a client-side automation tool.** They are complementary. Use wp-cli when you need full server access. Use WPA when you need remote access, fine-grained permissions, or safe AI tool use. Use both when your workflow spans both domains.

**WPA is not a Python library.** It is a CLI tool. While the `wpa` package is importable Python, the primary interface is the command line. Developers who need a programmatic Python interface to the WordPress REST API should consider `wordpress-api-client` or write directly against the REST API. WPA's value is in the CLI interface, the multi-site configuration system, the security defaults, and the command structure that makes WordPress management accessible from the terminal.

---

## 4. Design principles

### 4.1 Follow wp-cli conventions where the REST API allows

WPA command names, subcommand names, and flag names should match wp-cli conventions wherever the underlying REST API operation maps cleanly. A wp-cli user should be able to guess WPA commands without reading documentation. `wp post list` becomes `wpa post list`. `wp user create` becomes `wpa user create`. `wp comment approve 42` becomes `wpa comment approve 42`.

Where the REST API imposes different conventions (e.g., plugin identifiers as `folder/file.php` rather than slugs), WPA should accept both formats and translate as needed.

### 4.2 Be honest about boundaries

WPA should never pretend to support an operation it cannot perform via the REST API. If a user tries `wpa db export`, WPA should clearly explain that database operations require server access and suggest using wp-cli. Error messages for unsupported operations should be helpful, not cryptic.

The mapping matrix (see Reference Documents) explicitly documents every wp-cli command's REST API feasibility status. This transparency extends to the user experience.

### 4.3 Default to safety

Draft status by default for content creation. HTTPS enforcement for public URLs. Credentials in XDG config with restrictive permissions. Password input hidden. Status values validated. These defaults protect users (especially AI agents) from accidental damage. Destructive operations should require explicit confirmation or flags.

### 4.4 Structured output for machines, readable output for humans

The default output format should be human-readable (tables or clean text). A `--json` flag should produce machine-parseable JSON output that passes through the REST API's native response format. Both formats should be available for every command that returns data.

### 4.5 Minimal dependencies, maximum portability

WPA should work anywhere Python 3.9+ runs. Dependencies should be limited to well-maintained, widely-available packages. No C extensions, no system-level dependencies, no optional features that require additional installs.

### 4.6 Accessible to WordPress newcomers

While wp-cli parity is the command naming guide, WPA should not assume users know wp-cli. Help text, error messages, and documentation should explain what each command does in plain terms, not just reference wp-cli equivalents. A developer who has never used WordPress from the command line should be able to start with `wpa site add` and `wpa post list` without reading a wp-cli tutorial first.

---

## 5. Architecture

### 5.1 Package structure

```
wpa/
├── cli.py          # CLI entry point and argument parsing
├── config.py       # Site configuration management (XDG, .env)
├── publish.py      # Markdown-to-WordPress publishing
├── api.py          # REST API client layer (HTTP, auth, pagination)
├── post.py         # Post subcommand handlers
├── page.py         # Page subcommand handlers
├── user.py         # User subcommand handlers
├── comment.py      # Comment subcommand handlers
├── media.py        # Media subcommand handlers
├── term.py         # Term/taxonomy subcommand handlers
├── plugin.py       # Plugin subcommand handlers
├── menu.py         # Menu subcommand handlers
├── widget.py       # Widget subcommand handlers
├── option.py       # Settings/option subcommand handlers
├── format.py       # Output formatting (table, JSON, CSV)
└── __init__.py
```

### 5.2 API client layer

The `api.py` module handles all HTTP communication with WordPress REST API endpoints. It is responsible for:

- **Authentication:** Application Password authentication via HTTP Basic Auth over HTTPS
- **Base URL construction:** From site config, build `{WP_SITE_URL}/wp-json/wp/v2/` base path
- **Pagination:** Transparent handling of `X-WP-Total` / `X-WP-TotalPages` headers with automatic multi-page retrieval for list commands
- **Error handling:** Map HTTP status codes to meaningful error messages (401 = authentication failure, 403 = insufficient permissions, 404 = resource not found, etc.)
- **Retries:** Configurable retry with backoff for transient network errors
- **JSON response parsing:** All responses parsed as JSON; raw response available for debugging

### 5.3 Output formatting

The `format.py` module provides consistent output across all commands:

| Format | Flag | Description |
|---|---|---|
| Table | (default) | Human-readable aligned columns |
| JSON | `--json` | Raw REST API JSON response |
| IDs | `--ids` | Space-separated list of resource IDs |
| Count | `--count` | Numeric count of results |
| CSV | `--csv` | Comma-separated values with header row |

The `--fields` flag limits output to specific fields. The `--field` flag (singular) outputs a single field value per result, one per line.

### 5.4 Multi-site configuration

Site configurations are stored at `~/.config/wpa/<site-name>/.env` (respecting `XDG_CONFIG_HOME`). Each config contains:

```
WP_SITE_URL=https://example.com
WP_USER=your-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
WP_ADMIN_PATH=wp-admin
```

The `--site` flag selects a named config. With one config, it auto-selects. With multiple configs and no `--site` flag, WPA prompts for selection. This behavior is already implemented in v0.4.0.

---

## 6. Command structure

### 6.1 Implemented commands (v0.5.1)

| Command | Description |
|---|---|
| `wpa publish <file.md>` | Publish a markdown file as a WordPress page |
| `wpa page create <file.md>` | Create a page from markdown with frontmatter |
| `wpa site add` | Interactively add a new site configuration |
| `wpa site list` | List all configured sites |
| `wpa user list` | List users with `--role`, `--search`, `--format`, `--fields` |
| `wpa user create` | Create user with `--username`, `--email`, `--role`, `--password` |
| `wpa user update <id>` | Update user fields |
| `wpa user delete <id>` | Delete user with `--reassign` |
| `wpa --version` | Display WPA version |

### 6.2 Planned command groups

Based on the REST API mapping matrix, the following command groups are implementable and prioritized by value:

**Tier 1 — Core content management (highest priority)**

| Command Group | Key Subcommands | REST API Endpoint |
|---|---|---|
| `wpa post` | `list`, `get`, `create`, `update`, `delete` | `/wp/v2/posts` |
| `wpa page` | `list`, `get`, `create`, `update`, `delete` | `/wp/v2/pages` |
| `wpa user` | `list`, `get`, `create`, `update`, `delete`, `set-role` | `/wp/v2/users` |
| `wpa media` | `import`, `list`, `get`, `delete` | `/wp/v2/media` |

**Tier 2 — Content organization and moderation**

| Command Group | Key Subcommands | REST API Endpoint |
|---|---|---|
| `wpa comment` | `list`, `get`, `create`, `update`, `delete`, `approve`, `spam`, `trash` | `/wp/v2/comments` |
| `wpa term` | `list`, `get`, `create`, `update`, `delete` (for categories, tags, custom taxonomies) | `/wp/v2/categories`, `/wp/v2/tags`, etc. |
| `wpa category` | Alias for `wpa term` with `--taxonomy=category` | `/wp/v2/categories` |
| `wpa tag` | Alias for `wpa term` with `--taxonomy=post_tag` | `/wp/v2/tags` |

**Tier 3 — Site configuration and structure**

| Command Group | Key Subcommands | REST API Endpoint |
|---|---|---|
| `wpa plugin` | `list`, `get`, `install`, `activate`, `deactivate`, `delete` | `/wp/v2/plugins` |
| `wpa menu` | `list`, `create`, `delete`, plus `item` subgroup | `/wp/v2/menus`, `/wp/v2/menu-items` |
| `wpa widget` | `list`, `add`, `update`, `delete`, `deactivate` | `/wp/v2/widgets` |
| `wpa option` | `get`, `update`, `list` (registered settings only) | `/wp/v2/settings` |
| `wpa sidebar` | `list` | `/wp/v2/sidebars` |

**Tier 4 — Introspection and discovery**

| Command Group | Key Subcommands | REST API Endpoint |
|---|---|---|
| `wpa taxonomy` | `list`, `get` | `/wp/v2/taxonomies` |
| `wpa post-type` | `list`, `get` | `/wp/v2/types` |
| `wpa block` | `list`, `get` | `/wp/v2/block-types` |
| `wpa ability` | `list`, `get`, `run` | `/wp/v2/abilities` |
| `wpa api discover` | List all available REST API endpoints for a site | `GET /wp-json/` |

**Tier 5 — User security management**

| Command Group | Key Subcommands | REST API Endpoint |
|---|---|---|
| `wpa user application-password` | `list`, `create`, `delete`, `get` | `/wp/v2/users/<id>/application-passwords` |
| `wpa theme` | `list`, `get`, `is-active` (read-only) | `/wp/v2/themes` |

### 6.3 Global flags

| Flag | Description |
|---|---|
| `--site <name>` | Select a named site configuration |
| `--json` | Output as JSON |
| `--csv` | Output as CSV |
| `--ids` | Output only resource IDs |
| `--count` | Output only the count of results |
| `--fields <f1,f2>` | Limit output to specific fields |
| `--field <f>` | Output a single field per result |
| `--debug` | Show HTTP request/response details |
| `--version` | Display WPA version |
| `--help` | Show help for any command |

---

## 7. Implementation roadmap

### Phase 1: Package structure and user management (v0.4.0–v0.5.1) — COMPLETE

**Delivered:** Python package with subcommand CLI, PyPI distribution, multi-site config, user CRUD, shared output formatter, security hardening.

| Deliverable | Status |
|---|---|
| Package restructure (`wpa/` with `cli.py`, `config.py`, `publish.py`) | Shipped v0.4.0 |
| Subcommand CLI (`wpa publish`, `wpa page create`, `wpa site add/list`) | Shipped v0.4.0 |
| `wpa user list/create/update/delete` | Shipped v0.5.0 |
| `formatter.py` — shared output formatting (table, json, csv, tsv) with `--fields` | Shipped v0.5.0 |
| Security hardening (user ID validation, JSON error handling, response sanitization) | Shipped v0.5.1 |
| `CLAUDE.md` — agent-facing documentation for Claude Code | Shipped v0.5.1 |

### Phase 2: API client layer and post/page CRUD (v0.6.0)

**Goal:** Extract a reusable API client from existing modules, then implement the most-used content management commands.

| Deliverable | Details |
|---|---|
| `api.py` module | Reusable REST API client with auth, pagination, error handling, retries |
| Extend `formatter.py` | Add `--ids`, `--count`, and `--field` (singular) output modes |
| `wpa post list` | List posts with filtering (`--status`, `--author`, `--search`, `--per-page`) |
| `wpa post get <id>` | Get a single post by ID |
| `wpa post create` | Create post from CLI flags, `--from-file`, or stdin |
| `wpa post update <id>` | Update post fields |
| `wpa post delete <id>` | Delete/trash a post |
| `wpa page list/get/update/delete` | Expand page subcommand to full CRUD |
| Refactor `wpa publish` | Use new `api.py` layer; maintain backward compatibility |
| Refactor `wpa user` | Use new `api.py` layer; verify all existing tests pass |

**Definition of done:** All commands have tests, 99% coverage maintained, CI passing across 3 OS × 4 Python versions. No direct `requests` calls outside `api.py`.

### Phase 3: Media and user enhancements (v0.7.0)

| Deliverable | Details |
|---|---|
| `wpa media import <file>` | Upload local file or URL as media attachment |
| `wpa media list` | List media with filters |
| `wpa media get <id>` | Get media details |
| `wpa media delete <id>` | Delete media attachment |
| `wpa user get <id>` | Get user details |
| `wpa user set-role <id> <role>` | Set user role |

### Phase 4: Comments and terms (v0.8.0)

| Deliverable | Details |
|---|---|
| `wpa comment` subcommands | Full CRUD plus moderation (`approve`, `spam`, `trash`, `unapprove`, `unspam`) |
| `wpa term` subcommands | CRUD for any taxonomy (categories, tags, custom) |
| `wpa category` alias | Convenience alias for `wpa term --taxonomy=category` |
| `wpa tag` alias | Convenience alias for `wpa term --taxonomy=post_tag` |
| Reusable meta handler | Shared logic for `meta add/get/update/delete/list` across entities |

### Phase 5: Plugins, menus, and widgets (v0.9.0)

| Deliverable | Details |
|---|---|
| `wpa plugin` subcommands | `list`, `get`, `install`, `activate`, `deactivate`, `delete`, `search` |
| `wpa menu` subcommands | `list`, `create`, `delete` plus `item` sub-group |
| `wpa widget` subcommands | `list`, `add`, `update`, `delete`, `deactivate` |
| `wpa sidebar list` | List registered sidebars |
| `wpa option` subcommands | `get`, `update`, `list` for registered settings |

### Phase 6: Introspection and discovery (v0.10.0)

| Deliverable | Details |
|---|---|
| `wpa taxonomy list/get` | List/inspect registered taxonomies |
| `wpa post-type list/get` | List/inspect registered post types |
| `wpa block list/get` | List/inspect registered block types |
| `wpa api discover` | Enumerate all REST API endpoints and their methods for a site |
| `wpa theme list/get` | Read-only theme information |
| `wpa user application-password` | Manage application passwords for users |

### Phase 7: Polish and 1.0 (v1.0.0)

| Deliverable | Details |
|---|---|
| Shell completion | Tab completion for bash, zsh, fish |
| MCP server | Optional MCP (Model Context Protocol) server wrapper for direct LLM tool use |
| Comprehensive docs | Full documentation site or README expansion |
| Stable API contract | CLI interface locked for backward compatibility |
| PyPI 1.0 release | Stable release with semantic versioning commitment |

---

## 8. Reference documents

These documents are maintained alongside this PRD in the `wpa` repository and should be kept in sync as WP-CLI and the WordPress REST API evolve:

| Document | Purpose |
|---|---|
| `docs/wp-cli-command-inventory.md` | Complete catalog of all WP-CLI 2.12.0 commands and subcommands (46 top-level groups, ~280+ subcommands) |
| `docs/wp-cli-rest-api-mapping-matrix.md` | Classification of every WP-CLI command against REST API feasibility (FULL / PARTIAL / NOT POSSIBLE / N/A) |
| `docs/wpa-development-recommendations.md` | Prioritized development recommendations for the current sprint |
| `RELEASE-NOTES.md` | Per-version changelog |
| `CONTRIBUTING.md` | Contribution guidelines |
| `CLAUDE.md` | Agent-facing documentation for Claude Code |

---

## Appendix A: REST API endpoints used by WPA

| Endpoint | Methods | WPA Command Group |
|---|---|---|
| `/wp/v2/posts` | GET, POST | `wpa post` |
| `/wp/v2/posts/<id>` | GET, POST, DELETE | `wpa post` |
| `/wp/v2/pages` | GET, POST | `wpa page` |
| `/wp/v2/pages/<id>` | GET, POST, DELETE | `wpa page` |
| `/wp/v2/users` | GET, POST | `wpa user` |
| `/wp/v2/users/<id>` | GET, POST, DELETE | `wpa user` |
| `/wp/v2/users/<id>/application-passwords` | GET, POST | `wpa user application-password` |
| `/wp/v2/media` | GET, POST | `wpa media` |
| `/wp/v2/media/<id>` | GET, POST, DELETE | `wpa media` |
| `/wp/v2/comments` | GET, POST | `wpa comment` |
| `/wp/v2/comments/<id>` | GET, POST, DELETE | `wpa comment` |
| `/wp/v2/categories` | GET, POST | `wpa category` / `wpa term` |
| `/wp/v2/categories/<id>` | GET, POST, DELETE | `wpa category` / `wpa term` |
| `/wp/v2/tags` | GET, POST | `wpa tag` / `wpa term` |
| `/wp/v2/tags/<id>` | GET, POST, DELETE | `wpa tag` / `wpa term` |
| `/wp/v2/plugins` | GET, POST | `wpa plugin` |
| `/wp/v2/plugins/<plugin>` | GET, POST, DELETE | `wpa plugin` |
| `/wp/v2/menus` | GET, POST | `wpa menu` |
| `/wp/v2/menus/<id>` | GET, POST, DELETE | `wpa menu` |
| `/wp/v2/menu-items` | GET, POST | `wpa menu item` |
| `/wp/v2/menu-items/<id>` | GET, POST, DELETE | `wpa menu item` |
| `/wp/v2/menu-locations` | GET | `wpa menu location` |
| `/wp/v2/widgets` | GET, POST | `wpa widget` |
| `/wp/v2/widgets/<id>` | GET, POST, DELETE | `wpa widget` |
| `/wp/v2/sidebars` | GET | `wpa sidebar` |
| `/wp/v2/settings` | GET, POST | `wpa option` |
| `/wp/v2/taxonomies` | GET | `wpa taxonomy` |
| `/wp/v2/types` | GET | `wpa post-type` |
| `/wp/v2/block-types` | GET | `wpa block` |
| `/wp/v2/themes` | GET | `wpa theme` |
| `/wp/v2/abilities` | GET, POST | `wpa ability` |
| `/wp-json/` | GET | `wpa api discover` |

---

## Appendix B: Comparison with existing tools

| Capability | wp-cli | wpa | wordpress-api-client (Python lib) |
|---|---|---|---|
| CLI interface | Yes | Yes | No (programmatic only) |
| Requires server access | Yes (PHP + filesystem) | No | No |
| Authentication model | Server-side PHP user | Application Passwords (role-based) | Application Passwords / OAuth |
| Remote operation | Via SSH only | Native (HTTPS) | Native (HTTPS) |
| Multi-site management | One site at a time | Built-in multi-site config | Manual per-instance |
| JSON output | `--format=json` | `--json` (native REST API JSON) | Programmatic |
| AI agent safe | No (unrestricted access) | Yes (role-bounded permissions) | N/A (no CLI) |
| Command coverage | ~280+ commands | ~95 (REST API subset) | Varies |
| Plugin install/activate | Yes | Yes (via REST API) | Yes |
| Plugin update (new version) | Yes | No (REST API limitation) | No |
| Theme activate/install | Yes | No (REST API read-only) | No |
| Database operations | Yes | No | No |
| Core update | Yes | No | No |
| Credential security | wp-config.php on server | HTTPS + XDG config (600 perms) | Developer-managed |
| Audit trail | PHP-level hooks | HTTP request logs | Developer-managed |
