# WP-CLI to REST API Mapping Matrix

**Reference versions:**
- WP-CLI: 2.12.0 (current stable)
- WordPress REST API: wp/v2 (WordPress 6.9+)
- REST API reference: [developer.wordpress.org/rest-api/reference](https://developer.wordpress.org/rest-api/reference/)

**Purpose:** For each WP-CLI command, classify whether it can be implemented via the WordPress REST API, identify the corresponding endpoint, and document any gaps or behavioral differences. This document drives the `wpa` implementation roadmap.

**Document date:** 2026-03-21

---

## Classification key

Each WP-CLI command is assigned one of four statuses:

| Status | Meaning |
|---|---|
| **FULL** | Fully implementable via REST API with standard endpoints |
| **PARTIAL** | Partially implementable — some flags or behaviors have no REST API equivalent |
| **NOT POSSIBLE** | Requires filesystem, database, or PHP execution access — no REST API path |
| **N/A** | WP-CLI self-management command — not applicable to `wpa` |

---

## 1. wp ability

*WordPress Abilities API (WordPress 6.9+). REST API endpoints are being developed alongside this feature.*

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp ability list` | **FULL** | `GET /wp/v2/abilities` | Abilities API exposes REST endpoints |
| `wp ability get` | **FULL** | `GET /wp/v2/abilities/<name>` | |
| `wp ability run` | **FULL** | `POST /wp/v2/abilities/<name>/run` | |
| `wp ability exists` | **FULL** | `GET /wp/v2/abilities/<name>` | Check via HTTP status (200 vs 404) |
| `wp ability can-run` | **PARTIAL** | `GET /wp/v2/abilities/<name>` | Permission check embedded in response; may need authenticated request |
| `wp ability validate` | **PARTIAL** | — | Validation may be server-side only; test via run with dry-run if supported |

---

## 2. wp admin

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp admin` | **NOT POSSIBLE** | — | Opens browser to wp-admin; local OS operation. `wpa` could construct the URL and open it or print it |

---

## 3. wp block

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp block list` | **FULL** | `GET /wp/v2/block-types` | Lists registered block types |
| `wp block get` | **FULL** | `GET /wp/v2/block-types/<namespace>/<name>` | |

---

## 4. wp cache

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp cache add` | **NOT POSSIBLE** | — | Object cache is server-side in-memory (Memcached/Redis); no REST API |
| `wp cache decr` | **NOT POSSIBLE** | — | |
| `wp cache delete` | **NOT POSSIBLE** | — | |
| `wp cache flush` | **NOT POSSIBLE** | — | |
| `wp cache get` | **NOT POSSIBLE** | — | |
| `wp cache incr` | **NOT POSSIBLE** | — | |
| `wp cache replace` | **NOT POSSIBLE** | — | |
| `wp cache set` | **NOT POSSIBLE** | — | |
| `wp cache supports` | **NOT POSSIBLE** | — | |
| `wp cache type` | **NOT POSSIBLE** | — | |

**Reason:** The WP Object Cache operates entirely in server memory. No REST API endpoints exist for cache manipulation.

---

## 5. wp cap

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp cap add` | **NOT POSSIBLE** | — | Role capabilities are managed via PHP functions; no REST API endpoint |
| `wp cap list` | **NOT POSSIBLE** | — | Role/capability data is not exposed via REST API |
| `wp cap remove` | **NOT POSSIBLE** | — | |

**Reason:** WordPress REST API does not expose role/capability management endpoints. Roles are stored in the `wp_options` table as serialized data.

---

## 6. wp cli

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp cli alias` (all) | **N/A** | — | WP-CLI self-management |
| `wp cli cache` (all) | **N/A** | — | WP-CLI self-management |
| `wp cli check-update` | **N/A** | — | WP-CLI self-management |
| `wp cli cmd-dump` | **N/A** | — | WP-CLI self-management |
| `wp cli completions` | **N/A** | — | WP-CLI self-management |
| `wp cli has-command` | **N/A** | — | WP-CLI self-management |
| `wp cli info` | **N/A** | — | WP-CLI self-management |
| `wp cli param-dump` | **N/A** | — | WP-CLI self-management |
| `wp cli update` | **N/A** | — | WP-CLI self-management |
| `wp cli version` | **N/A** | — | WP-CLI self-management; `wpa --version` already exists |

---

## 7. wp comment

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp comment approve` | **FULL** | `POST /wp/v2/comments/<id>` | Set `status=approved` |
| `wp comment count` | **PARTIAL** | `GET /wp/v2/comments` | Use response headers `X-WP-Total`; no per-status breakdown in single call |
| `wp comment create` | **FULL** | `POST /wp/v2/comments` | |
| `wp comment delete` | **FULL** | `DELETE /wp/v2/comments/<id>` | Use `?force=true` to bypass trash |
| `wp comment exists` | **FULL** | `GET /wp/v2/comments/<id>` | Check HTTP status (200 vs 404) |
| `wp comment generate` | **NOT POSSIBLE** | — | Bulk dummy data generation is a server-side operation |
| `wp comment get` | **FULL** | `GET /wp/v2/comments/<id>` | |
| `wp comment list` | **FULL** | `GET /wp/v2/comments` | Supports `status`, `post`, `search`, `orderby`, `order`, `per_page` params |
| `wp comment meta add` | **FULL** | `POST /wp/v2/comments/<id>` | Via meta fields in update payload (requires `register_meta` with `show_in_rest`) |
| `wp comment meta delete` | **FULL** | `POST /wp/v2/comments/<id>` | Set meta value to null/empty |
| `wp comment meta get` | **FULL** | `GET /wp/v2/comments/<id>` | Meta included in response if registered with `show_in_rest` |
| `wp comment meta list` | **PARTIAL** | `GET /wp/v2/comments/<id>` | Only meta registered with `show_in_rest=true` is visible |
| `wp comment meta patch` | **PARTIAL** | `POST /wp/v2/comments/<id>` | Nested updates depend on meta registration |
| `wp comment meta pluck` | **PARTIAL** | `GET /wp/v2/comments/<id>` | Client-side extraction from response |
| `wp comment meta update` | **FULL** | `POST /wp/v2/comments/<id>` | Via meta fields in update payload |
| `wp comment recount` | **NOT POSSIBLE** | — | Recalculates DB-level comment counts; requires direct DB access |
| `wp comment spam` | **FULL** | `POST /wp/v2/comments/<id>` | Set `status=spam` |
| `wp comment status` | **FULL** | `GET /wp/v2/comments/<id>` | Extract `status` field from response |
| `wp comment trash` | **FULL** | `DELETE /wp/v2/comments/<id>` | Without `?force=true` (default is trash) |
| `wp comment unapprove` | **FULL** | `POST /wp/v2/comments/<id>` | Set `status=hold` |
| `wp comment unspam` | **FULL** | `POST /wp/v2/comments/<id>` | Set `status=approved` or `status=hold` |
| `wp comment untrash` | **NOT POSSIBLE** | — | REST API does not support untrashing; trashed comments need server-side recovery |
| `wp comment update` | **FULL** | `POST /wp/v2/comments/<id>` | |

---

## 8. wp config

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp config create` | **NOT POSSIBLE** | — | Filesystem write to wp-config.php |
| `wp config delete` | **NOT POSSIBLE** | — | Filesystem modification |
| `wp config edit` | **NOT POSSIBLE** | — | Opens local editor |
| `wp config get` | **NOT POSSIBLE** | — | Reads wp-config.php directly |
| `wp config has` | **NOT POSSIBLE** | — | Reads wp-config.php directly |
| `wp config is-true` | **NOT POSSIBLE** | — | Reads wp-config.php directly |
| `wp config list` | **NOT POSSIBLE** | — | Reads wp-config.php directly |
| `wp config path` | **NOT POSSIBLE** | — | Filesystem path operation |
| `wp config set` | **NOT POSSIBLE** | — | Filesystem write |
| `wp config shuffle-salts` | **NOT POSSIBLE** | — | Filesystem write |

**Reason:** wp-config.php is a server-side PHP file. All operations require filesystem access.

---

## 9. wp core

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp core check-update` | **NOT POSSIBLE** | — | Checks WordPress.org update API; requires server-side version comparison |
| `wp core download` | **NOT POSSIBLE** | — | Filesystem download and extraction |
| `wp core install` | **NOT POSSIBLE** | — | Full WordPress installation process |
| `wp core is-installed` | **PARTIAL** | `GET /wp-json/` | If the REST API index responds, WordPress is installed and running |
| `wp core multisite-convert` | **NOT POSSIBLE** | — | Requires wp-config.php and database modifications |
| `wp core multisite-install` | **NOT POSSIBLE** | — | Full multisite installation process |
| `wp core update` | **NOT POSSIBLE** | — | Filesystem download and replacement of core files |
| `wp core update-db` | **NOT POSSIBLE** | — | Database schema migration |
| `wp core verify-checksums` | **NOT POSSIBLE** | — | Filesystem checksum verification |
| `wp core version` | **PARTIAL** | `GET /wp-json/` | Response includes `name` and `description` but not explicit version; can use `GET /wp/v2/settings` if authenticated (returns `wp_version` indirectly) |

---

## 10. wp cron

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp cron event delete` | **NOT POSSIBLE** | — | WP-Cron events stored in `cron` option; no REST API exposure |
| `wp cron event list` | **NOT POSSIBLE** | — | |
| `wp cron event run` | **NOT POSSIBLE** | — | |
| `wp cron event schedule` | **NOT POSSIBLE** | — | |
| `wp cron event unschedule` | **NOT POSSIBLE** | — | |
| `wp cron schedule list` | **NOT POSSIBLE** | — | |
| `wp cron test` | **NOT POSSIBLE** | — | |

**Reason:** WP-Cron is an internal scheduling mechanism stored as a serialized array in the `cron` option. No REST API endpoints exist.

---

## 11. wp db

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp db` subcommands | **NOT POSSIBLE** | — | Direct database operations via MySQL credentials |

**Reason:** All 16 `wp db` subcommands require direct database access via MySQL/MariaDB credentials stored in wp-config.php. No REST API path exists.

---

## 12. wp dist-archive

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp dist-archive` | **NOT POSSIBLE** | — | Filesystem archive creation |

---

## 13. wp embed

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp embed cache clear` | **NOT POSSIBLE** | — | Modifies post meta cache entries directly |
| `wp embed cache find` | **NOT POSSIBLE** | — | Queries internal cache posts |
| `wp embed cache trigger` | **NOT POSSIBLE** | — | Triggers server-side oEmbed processing |
| `wp embed fetch` | **NOT POSSIBLE** | — | Server-side oEmbed discovery and rendering |
| `wp embed handler list` | **NOT POSSIBLE** | — | PHP-registered handlers; no REST API exposure |
| `wp embed provider list` | **NOT POSSIBLE** | — | PHP-registered providers; no REST API exposure |
| `wp embed provider match` | **NOT POSSIBLE** | — | Server-side provider matching logic |

**Reason:** oEmbed functionality is handled server-side via PHP hooks and provider registrations. The REST API does not expose embed management endpoints.

---

## 14. wp eval

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp eval` | **NOT POSSIBLE** | — | Executes arbitrary PHP code on the server |

---

## 15. wp eval-file

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp eval-file` | **NOT POSSIBLE** | — | Loads and executes a PHP file on the server |

---

## 16. wp export

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp export` | **NOT POSSIBLE** | — | Generates WXR XML export file server-side |

---

## 17. wp find

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp find` | **NOT POSSIBLE** | — | Scans filesystem for WordPress installations |

---

## 18. wp help

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp help` | **N/A** | — | WP-CLI self-management; `wpa` will implement its own `--help` |

---

## 19. wp i18n

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp i18n make-json` | **NOT POSSIBLE** | — | Filesystem operation on PO/JSON files |
| `wp i18n make-mo` | **NOT POSSIBLE** | — | Filesystem compilation of PO to MO |
| `wp i18n make-php` | **NOT POSSIBLE** | — | Filesystem compilation of PO to PHP |
| `wp i18n make-pot` | **NOT POSSIBLE** | — | Source code scanning for translatable strings |
| `wp i18n update-po` | **NOT POSSIBLE** | — | Filesystem operation on PO files |

**Reason:** All i18n commands operate on local source files and translation files. They don't interact with a running WordPress site.

---

## 20. wp import

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp import` | **NOT POSSIBLE** | — | Server-side WXR import requiring filesystem access and PHP execution |

---

## 21. wp language

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp language` subcommands | **NOT POSSIBLE** | — | Language pack management requires filesystem access to download, install, and delete translation files |

**Reason:** Language packs are ZIP files downloaded to `wp-content/languages/`. All operations require filesystem access.

---

## 22. wp maintenance-mode

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp maintenance-mode activate` | **NOT POSSIBLE** | — | Creates `.maintenance` file in WordPress root |
| `wp maintenance-mode deactivate` | **NOT POSSIBLE** | — | Deletes `.maintenance` file |
| `wp maintenance-mode is-active` | **PARTIAL** | — | Could detect via failed API responses, but unreliable |
| `wp maintenance-mode status` | **PARTIAL** | — | Same as above |

---

## 23. wp media

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp media fix-orientation` | **NOT POSSIBLE** | — | Server-side image manipulation (GD/Imagick) |
| `wp media image-size` | **NOT POSSIBLE** | — | PHP-registered image sizes; not exposed via REST API |
| `wp media import` | **FULL** | `POST /wp/v2/media` | Upload via multipart form data with `Content-Disposition` header. Supports `title`, `alt_text`, `caption`, `description`, `post` (parent) |
| `wp media regenerate` | **NOT POSSIBLE** | — | Server-side thumbnail regeneration requiring filesystem + image library |

---

## 24. wp menu

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp menu create` | **FULL** | `POST /wp/v2/menus` | |
| `wp menu delete` | **FULL** | `DELETE /wp/v2/menus/<id>` | |
| `wp menu item add-custom` | **FULL** | `POST /wp/v2/menu-items` | Set `type=custom`, `url`, `title` |
| `wp menu item add-post` | **FULL** | `POST /wp/v2/menu-items` | Set `type=post_type`, `object_id` |
| `wp menu item add-term` | **FULL** | `POST /wp/v2/menu-items` | Set `type=taxonomy`, `object_id` |
| `wp menu item delete` | **FULL** | `DELETE /wp/v2/menu-items/<id>` | |
| `wp menu item list` | **FULL** | `GET /wp/v2/menu-items?menus=<id>` | |
| `wp menu item update` | **FULL** | `POST /wp/v2/menu-items/<id>` | |
| `wp menu list` | **FULL** | `GET /wp/v2/menus` | |
| `wp menu location assign` | **PARTIAL** | — | Menu locations are theme-dependent; may require settings update or custom endpoint |
| `wp menu location list` | **FULL** | `GET /wp/v2/menu-locations` | |
| `wp menu location remove` | **PARTIAL** | — | Same constraint as assign |

---

## 25. wp network

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp network meta` (all) | **NOT POSSIBLE** | — | Network meta is multisite-specific; no REST API endpoints |

---

## 26. wp option

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp option add` | **PARTIAL** | `POST /wp/v2/settings` | Only options registered with `show_in_rest=true` are accessible |
| `wp option delete` | **NOT POSSIBLE** | — | REST API settings endpoint only supports get/update, not delete |
| `wp option get` | **PARTIAL** | `GET /wp/v2/settings` | Only `show_in_rest` options. Core options like `blogname`, `blogdescription`, `site_url`, `timezone_string`, `date_format`, `time_format`, `posts_per_page`, etc. are included |
| `wp option list` | **PARTIAL** | `GET /wp/v2/settings` | Returns only registered settings, not the full wp_options table |
| `wp option patch` | **PARTIAL** | `POST /wp/v2/settings` | Only for registered settings |
| `wp option pluck` | **PARTIAL** | `GET /wp/v2/settings` | Client-side extraction |
| `wp option set` | **PARTIAL** | `POST /wp/v2/settings` | Only `show_in_rest` options |
| `wp option update` | **PARTIAL** | `POST /wp/v2/settings` | Same as set |

**Key limitation:** `wp option` can read/write any row in the `wp_options` table. The REST API only exposes options explicitly registered with `show_in_rest=true` via the `/wp/v2/settings` endpoint. This includes core WordPress settings but excludes most plugin-specific options unless the plugin registers them.

---

## 27. wp package

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp package` subcommands | **N/A** | — | WP-CLI package management; not applicable to `wpa` |

---

## 28. wp plugin

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp plugin activate` | **FULL** | `POST /wp/v2/plugins/<plugin>` | Set `status=active` |
| `wp plugin auto-updates disable` | **FULL** | `POST /wp/v2/plugins/<plugin>` | Set `auto_update=false` (WP 5.5+) |
| `wp plugin auto-updates enable` | **FULL** | `POST /wp/v2/plugins/<plugin>` | Set `auto_update=true` |
| `wp plugin auto-updates status` | **FULL** | `GET /wp/v2/plugins/<plugin>` | Check `auto_update` field |
| `wp plugin deactivate` | **FULL** | `POST /wp/v2/plugins/<plugin>` | Set `status=inactive` |
| `wp plugin delete` | **FULL** | `DELETE /wp/v2/plugins/<plugin>` | Deletes plugin files |
| `wp plugin get` | **FULL** | `GET /wp/v2/plugins/<plugin>` | Returns name, status, version, description, etc. |
| `wp plugin install` | **FULL** | `POST /wp/v2/plugins` | Provide `slug` to install from WordPress.org |
| `wp plugin is-active` | **FULL** | `GET /wp/v2/plugins/<plugin>` | Check `status` field |
| `wp plugin is-installed` | **FULL** | `GET /wp/v2/plugins/<plugin>` | Check HTTP status (200 vs 404) |
| `wp plugin list` | **FULL** | `GET /wp/v2/plugins` | Returns all installed plugins with status, version |
| `wp plugin path` | **NOT POSSIBLE** | — | Server filesystem path |
| `wp plugin search` | **FULL** | `GET /wp/v2/plugins?search=<term>` | Searches WordPress.org directory |
| `wp plugin status` | **FULL** | `GET /wp/v2/plugins/<plugin>` | |
| `wp plugin toggle` | **FULL** | `POST /wp/v2/plugins/<plugin>` | Read current status, then set opposite |
| `wp plugin uninstall` | **PARTIAL** | `DELETE /wp/v2/plugins/<plugin>` | REST API deletes files but doesn't run uninstall hooks the same way |
| `wp plugin update` | **NOT POSSIBLE** | — | REST API `/wp/v2/plugins` does not support updating to newer versions |
| `wp plugin verify-checksums` | **NOT POSSIBLE** | — | Server-side file checksum verification |

**Note:** The REST API plugins endpoint (`/wp/v2/plugins`) was added in WordPress 5.5. It covers install, activate, deactivate, and delete. However, updating a plugin to a newer version is not supported via REST API — that requires filesystem operations (download, extract, replace files). The plugin identifier format for REST API is `plugin-folder/plugin-file.php`.

---

## 29. wp post

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp post create` | **FULL** | `POST /wp/v2/posts` | Supports `title`, `content`, `status`, `slug`, `categories`, `tags`, `featured_media`, `meta`, etc. |
| `wp post delete` | **FULL** | `DELETE /wp/v2/posts/<id>` | `?force=true` to bypass trash |
| `wp post edit` | **NOT POSSIBLE** | — | Launches local system editor |
| `wp post exists` | **FULL** | `GET /wp/v2/posts/<id>` | Check HTTP status |
| `wp post generate` | **NOT POSSIBLE** | — | Bulk dummy data generation |
| `wp post get` | **FULL** | `GET /wp/v2/posts/<id>` | Use `?_embed` for linked resources |
| `wp post list` | **FULL** | `GET /wp/v2/posts` | Supports `status`, `search`, `author`, `categories`, `tags`, `before`, `after`, `orderby`, `order`, `per_page`, `page`, `slug` |
| `wp post meta add` | **FULL** | `POST /wp/v2/posts/<id>` | Via `meta` field (requires `register_meta` with `show_in_rest`) |
| `wp post meta delete` | **FULL** | `POST /wp/v2/posts/<id>` | Set meta to null/empty |
| `wp post meta get` | **FULL** | `GET /wp/v2/posts/<id>` | Meta in response if registered |
| `wp post meta list` | **PARTIAL** | `GET /wp/v2/posts/<id>` | Only `show_in_rest` meta visible |
| `wp post meta patch` | **PARTIAL** | `POST /wp/v2/posts/<id>` | Depends on meta registration |
| `wp post meta pluck` | **PARTIAL** | `GET /wp/v2/posts/<id>` | Client-side extraction |
| `wp post meta update` | **FULL** | `POST /wp/v2/posts/<id>` | Via `meta` field |
| `wp post term add` | **FULL** | `POST /wp/v2/posts/<id>` | Update `categories` or `tags` arrays |
| `wp post term list` | **FULL** | `GET /wp/v2/posts/<id>` | Use `?_embed` to include term details |
| `wp post term remove` | **FULL** | `POST /wp/v2/posts/<id>` | Update arrays to exclude term IDs |
| `wp post term set` | **FULL** | `POST /wp/v2/posts/<id>` | Replace `categories`/`tags` arrays entirely |
| `wp post update` | **FULL** | `POST /wp/v2/posts/<id>` | |
| `wp post url-to-id` | **NOT POSSIBLE** | — | Server-side URL resolution via `url_to_postid()` |

**Note:** For custom post types, the REST API endpoint changes (e.g., `/wp/v2/pages` for pages). Custom post types must have `show_in_rest=true` and a `rest_base` defined. The `wpa publish` command already handles pages via `/wp/v2/pages`.

---

## 30. wp post-type

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp post-type get` | **FULL** | `GET /wp/v2/types/<type>` | |
| `wp post-type list` | **FULL** | `GET /wp/v2/types` | Only post types with `show_in_rest=true` |

---

## 31. wp profile

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp profile` subcommands | **NOT POSSIBLE** | — | Server-side PHP profiling requiring direct execution |

---

## 32. wp rewrite

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp rewrite flush` | **NOT POSSIBLE** | — | Server-side rewrite rule regeneration |
| `wp rewrite list` | **NOT POSSIBLE** | — | PHP-registered rewrite rules; not exposed via REST API |
| `wp rewrite structure` | **NOT POSSIBLE** | — | Modifies permalink settings requiring server access |

---

## 33. wp role

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp role create` | **NOT POSSIBLE** | — | Roles stored as serialized option; no REST API endpoint |
| `wp role delete` | **NOT POSSIBLE** | — | |
| `wp role exists` | **NOT POSSIBLE** | — | |
| `wp role list` | **NOT POSSIBLE** | — | |
| `wp role reset` | **NOT POSSIBLE** | — | |

**Reason:** WordPress roles are stored as a serialized array in the `wp_user_roles` option. The REST API does not expose role management.

---

## 34. wp scaffold

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp scaffold` subcommands | **NOT POSSIBLE** | — | Code generation to local filesystem |

---

## 35. wp search-replace

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp search-replace` | **NOT POSSIBLE** | — | Direct database search and replace across all tables |

---

## 36. wp server

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp server` | **NOT POSSIBLE** | — | Launches local PHP dev server |

---

## 37. wp shell

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp shell` | **NOT POSSIBLE** | — | Interactive PHP REPL |

---

## 38. wp sidebar

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp sidebar list` | **FULL** | `GET /wp/v2/sidebars` | |

---

## 39. wp site

*Multisite-specific commands. Most require network admin access.*

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp site activate` | **NOT POSSIBLE** | — | Multisite site management; no REST API |
| `wp site archive` | **NOT POSSIBLE** | — | |
| `wp site create` | **NOT POSSIBLE** | — | |
| `wp site deactivate` | **NOT POSSIBLE** | — | |
| `wp site delete` | **NOT POSSIBLE** | — | |
| `wp site empty` | **NOT POSSIBLE** | — | |
| `wp site list` | **NOT POSSIBLE** | — | |
| `wp site mature` | **NOT POSSIBLE** | — | |
| `wp site meta` (all) | **NOT POSSIBLE** | — | |
| `wp site option` (all) | **NOT POSSIBLE** | — | |
| `wp site private` | **NOT POSSIBLE** | — | |
| `wp site public` | **NOT POSSIBLE** | — | |
| `wp site spam` | **NOT POSSIBLE** | — | |
| `wp site switch-language` | **NOT POSSIBLE** | — | |
| `wp site unarchive` | **NOT POSSIBLE** | — | |
| `wp site unmature` | **NOT POSSIBLE** | — | |
| `wp site unspam` | **NOT POSSIBLE** | — | |

**Reason:** The REST API does not expose multisite site management endpoints. Note: `wpa site` already uses this namespace for connection config management, which is a different concept.

---

## 40. wp super-admin

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp super-admin` subcommands | **NOT POSSIBLE** | — | Multisite super admin management; no REST API |

---

## 41. wp taxonomy

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp taxonomy get` | **FULL** | `GET /wp/v2/taxonomies/<taxonomy>` | |
| `wp taxonomy list` | **FULL** | `GET /wp/v2/taxonomies` | Only taxonomies with `show_in_rest=true` |

---

## 42. wp term

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp term create` | **FULL** | `POST /wp/v2/<taxonomy_rest_base>` | e.g., `/wp/v2/categories`, `/wp/v2/tags` |
| `wp term delete` | **FULL** | `DELETE /wp/v2/<taxonomy_rest_base>/<id>` | |
| `wp term generate` | **NOT POSSIBLE** | — | Bulk dummy data generation |
| `wp term get` | **FULL** | `GET /wp/v2/<taxonomy_rest_base>/<id>` | |
| `wp term list` | **FULL** | `GET /wp/v2/<taxonomy_rest_base>` | Supports `search`, `orderby`, `order`, `per_page`, `page`, `parent`, `slug` |
| `wp term meta add` | **FULL** | `POST /wp/v2/<taxonomy_rest_base>/<id>` | Via `meta` field (requires `register_meta` with `show_in_rest`) |
| `wp term meta delete` | **FULL** | `POST /wp/v2/<taxonomy_rest_base>/<id>` | |
| `wp term meta get` | **FULL** | `GET /wp/v2/<taxonomy_rest_base>/<id>` | |
| `wp term meta list` | **PARTIAL** | `GET /wp/v2/<taxonomy_rest_base>/<id>` | Only `show_in_rest` meta |
| `wp term meta patch` | **PARTIAL** | `POST /wp/v2/<taxonomy_rest_base>/<id>` | |
| `wp term meta pluck` | **PARTIAL** | `GET /wp/v2/<taxonomy_rest_base>/<id>` | Client-side extraction |
| `wp term meta update` | **FULL** | `POST /wp/v2/<taxonomy_rest_base>/<id>` | |
| `wp term migrate` | **NOT POSSIBLE** | — | Requires direct database manipulation |
| `wp term recount` | **NOT POSSIBLE** | — | Recalculates DB-level term counts |
| `wp term update` | **FULL** | `POST /wp/v2/<taxonomy_rest_base>/<id>` | |

**Note:** The REST API endpoint varies by taxonomy. Categories use `/wp/v2/categories`, tags use `/wp/v2/tags`, and custom taxonomies use their registered `rest_base`. The taxonomy REST base can be discovered via `/wp/v2/taxonomies`.

---

## 43. wp theme

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp theme activate` | **NOT POSSIBLE** | — | REST API themes endpoint is read-only for theme status |
| `wp theme auto-updates disable` | **NOT POSSIBLE** | — | Not exposed via REST API |
| `wp theme auto-updates enable` | **NOT POSSIBLE** | — | |
| `wp theme auto-updates status` | **NOT POSSIBLE** | — | |
| `wp theme delete` | **NOT POSSIBLE** | — | Filesystem operation |
| `wp theme disable` | **NOT POSSIBLE** | — | Multisite only |
| `wp theme enable` | **NOT POSSIBLE** | — | Multisite only |
| `wp theme get` | **FULL** | `GET /wp/v2/themes/<stylesheet>` | Returns name, version, description, author, etc. |
| `wp theme install` | **NOT POSSIBLE** | — | Filesystem download and extraction |
| `wp theme is-active` | **FULL** | `GET /wp/v2/themes/<stylesheet>` | Check `status` field |
| `wp theme is-installed` | **FULL** | `GET /wp/v2/themes` | Check if theme appears in list |
| `wp theme list` | **FULL** | `GET /wp/v2/themes` | |
| `wp theme mod get` | **PARTIAL** | `GET /wp/v2/settings` | Some theme mods exposed as settings |
| `wp theme mod list` | **NOT POSSIBLE** | — | Theme mods stored as options; not fully exposed |
| `wp theme mod remove` | **NOT POSSIBLE** | — | |
| `wp theme mod set` | **PARTIAL** | `POST /wp/v2/settings` | Only if registered with `show_in_rest` |
| `wp theme path` | **NOT POSSIBLE** | — | Server filesystem path |
| `wp theme search` | **NOT POSSIBLE** | — | No REST API endpoint for WordPress.org theme directory search |
| `wp theme status` | **FULL** | `GET /wp/v2/themes/<stylesheet>` | |
| `wp theme update` | **NOT POSSIBLE** | — | Filesystem download and replacement |

**Note:** Unlike the plugins REST API (which supports install, activate, deactivate, delete), the themes REST API is much more limited — primarily read-only. Theme activation, installation, and deletion are not supported via REST API.

---

## 44. wp transient

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| All `wp transient` subcommands | **NOT POSSIBLE** | — | Transients stored in `wp_options` or object cache; no REST API |

---

## 45. wp user

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp user add-cap` | **NOT POSSIBLE** | — | Individual user capabilities not exposed via REST API |
| `wp user add-role` | **PARTIAL** | `POST /wp/v2/users/<id>` | Can add roles via `roles` array, but REST API replaces roles rather than adding |
| `wp user application-password create` | **FULL** | `POST /wp/v2/users/<id>/application-passwords` | |
| `wp user application-password delete` | **FULL** | `DELETE /wp/v2/users/<id>/application-passwords/<uuid>` | |
| `wp user application-password exists` | **FULL** | `GET /wp/v2/users/<id>/application-passwords/<uuid>` | Check HTTP status |
| `wp user application-password get` | **FULL** | `GET /wp/v2/users/<id>/application-passwords/<uuid>` | |
| `wp user application-password list` | **FULL** | `GET /wp/v2/users/<id>/application-passwords` | |
| `wp user application-password update` | **FULL** | `POST /wp/v2/users/<id>/application-passwords/<uuid>` | |
| `wp user check-password` | **NOT POSSIBLE** | — | Server-side password hash verification |
| `wp user create` | **FULL** | `POST /wp/v2/users` | Supports `username`, `email`, `password`, `roles`, `first_name`, `last_name`, `url`, `description`, `slug`, `locale` |
| `wp user delete` | **FULL** | `DELETE /wp/v2/users/<id>` | Requires `force=true` and `reassign=<id>` |
| `wp user exists` | **FULL** | `GET /wp/v2/users/<id>` | Check HTTP status |
| `wp user generate` | **NOT POSSIBLE** | — | Bulk dummy data generation |
| `wp user get` | **FULL** | `GET /wp/v2/users/<id>` | |
| `wp user import-csv` | **NOT POSSIBLE** | — | Bulk import requiring CSV parsing and user creation loop |
| `wp user list` | **FULL** | `GET /wp/v2/users` | Supports `roles`, `search`, `orderby`, `order`, `per_page`, `page`, `slug`, `who` |
| `wp user list-caps` | **NOT POSSIBLE** | — | Individual capabilities not exposed |
| `wp user meta add` | **FULL** | `POST /wp/v2/users/<id>` | Via `meta` field (requires `register_meta` with `show_in_rest`) |
| `wp user meta delete` | **FULL** | `POST /wp/v2/users/<id>` | |
| `wp user meta get` | **FULL** | `GET /wp/v2/users/<id>` | |
| `wp user meta list` | **PARTIAL** | `GET /wp/v2/users/<id>` | Only `show_in_rest` meta |
| `wp user meta patch` | **PARTIAL** | `POST /wp/v2/users/<id>` | |
| `wp user meta pluck` | **PARTIAL** | `GET /wp/v2/users/<id>` | Client-side extraction |
| `wp user meta update` | **FULL** | `POST /wp/v2/users/<id>` | |
| `wp user remove-cap` | **NOT POSSIBLE** | — | Individual capabilities not exposed |
| `wp user remove-role` | **PARTIAL** | `POST /wp/v2/users/<id>` | Can update `roles` array but REST API replaces, not removes |
| `wp user reset-password` | **NOT POSSIBLE** | — | Server-side password reset email; no REST API |
| `wp user session destroy` | **NOT POSSIBLE** | — | Session tokens stored in user meta as serialized data |
| `wp user session list` | **NOT POSSIBLE** | — | |
| `wp user set-role` | **FULL** | `POST /wp/v2/users/<id>` | Set `roles` array |
| `wp user signup` (all) | **NOT POSSIBLE** | — | Multisite signup management |
| `wp user spam` | **NOT POSSIBLE** | — | Multisite only |
| `wp user term add` | **NOT POSSIBLE** | — | User taxonomy terms not commonly REST-exposed |
| `wp user term list` | **NOT POSSIBLE** | — | |
| `wp user term remove` | **NOT POSSIBLE** | — | |
| `wp user unspam` | **NOT POSSIBLE** | — | Multisite only |
| `wp user update` | **FULL** | `POST /wp/v2/users/<id>` | Supports `email`, `first_name`, `last_name`, `url`, `description`, `locale`, `nickname`, `slug`, `roles`, `password`, `meta` |

---

## 46. wp widget

| WP-CLI Command | Status | REST API Endpoint | Notes |
|---|---|---|---|
| `wp widget add` | **FULL** | `POST /wp/v2/widgets` | Requires `id_base`, `sidebar`, `instance` |
| `wp widget deactivate` | **FULL** | `POST /wp/v2/widgets/<id>` | Move to `wp_inactive_widgets` sidebar |
| `wp widget delete` | **FULL** | `DELETE /wp/v2/widgets/<id>` | |
| `wp widget list` | **FULL** | `GET /wp/v2/widgets?sidebar=<id>` | |
| `wp widget move` | **PARTIAL** | `POST /wp/v2/widgets/<id>` | Update `sidebar` field; position ordering may require multiple calls |
| `wp widget reset` | **PARTIAL** | — | Would require deleting all widgets in a sidebar; no single REST API call |
| `wp widget update` | **FULL** | `POST /wp/v2/widgets/<id>` | Update `instance` settings |

---

## Summary

### Coverage by status

| Status | Count | Percentage |
|---|---|---|
| **FULL** | ~95 | ~34% |
| **PARTIAL** | ~35 | ~12% |
| **NOT POSSIBLE** | ~130 | ~46% |
| **N/A** (WP-CLI self-management) | ~20 | ~7% |

### Fully implementable command groups (best candidates for wpa)

These command groups have the highest concentration of FULL-status commands and should form the core of `wpa`:

1. **wp post** — CRUD, meta, terms all map cleanly
2. **wp user** — CRUD, roles, application passwords, meta
3. **wp comment** — CRUD, moderation, meta
4. **wp term** (categories/tags) — Full CRUD and meta
5. **wp media** — Upload/create attachments
6. **wp plugin** — List, install, activate, deactivate, delete
7. **wp menu** — Full CRUD for menus and menu items
8. **wp widget** — Add, update, delete, list widgets
9. **wp sidebar** — List sidebars
10. **wp taxonomy** / **wp post-type** — Read-only introspection
11. **wp option** (partial) — Read/update registered settings
12. **wp block** — List/get block types
13. **wp ability** — New Abilities API commands

### Command groups with zero REST API coverage

These are entirely server-side and will never be implementable via REST API without custom endpoints:

`wp cache`, `wp config`, `wp core` (mostly), `wp cron`, `wp db`, `wp embed`, `wp eval`, `wp eval-file`, `wp export`, `wp find`, `wp i18n`, `wp import`, `wp language`, `wp network`, `wp profile`, `wp rewrite`, `wp role`, `wp scaffold`, `wp search-replace`, `wp server`, `wp shell`, `wp site` (multisite), `wp super-admin`, `wp transient`

### Key architectural constraints

1. **Meta fields:** The REST API only exposes meta fields registered with `show_in_rest=true`. This is the biggest gap vs. wp-cli, which can access all meta directly from the database. `wpa` should document this limitation clearly.

2. **Pagination:** All list endpoints use `X-WP-Total` and `X-WP-TotalPages` headers with `per_page` (max 100) and `page` parameters. `wpa` needs to handle pagination transparently for list commands.

3. **Authentication scope:** REST API responses vary based on the authenticated user's capabilities. An Editor cannot create users; a Subscriber sees limited data. wp-cli bypasses all capability checks. `wpa` should surface permission errors clearly.

4. **Plugin identifier format:** The REST API uses `folder/file.php` format for plugin identifiers (e.g., `akismet/akismet.php`), while wp-cli uses the slug (`akismet`). `wpa` should accept both formats.

5. **Theme REST API limitations:** Unlike plugins, the themes REST API is mostly read-only. Theme activation, installation, deletion, and auto-update management are not available via REST API.

6. **Custom post types and taxonomies:** REST API access requires `show_in_rest=true` in the post type/taxonomy registration. Not all custom types are REST-accessible. `wpa` can use the discovery endpoint (`/wp-json/`) to detect available types.
