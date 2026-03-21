# WP-CLI Command Inventory

**Reference version:** WP-CLI 2.12.0 (current stable release as of March 2026)
**Source:** [developer.wordpress.org/cli/commands](https://developer.wordpress.org/cli/commands/)
**Purpose:** Complete catalog of all WP-CLI commands and subcommands, to serve as the template for `wpa` REST API implementation planning.
**Document date:** 2026-03-21

---

## How to read this document

Each top-level command group is listed with its description and all subcommands. Commands marked with `(no subcommands)` are standalone commands invoked directly. Nested subcommands (e.g., `wp post meta add`) are listed under their parent.

---

## 1. wp ability

Lists, inspects, and executes abilities registered via the WordPress Abilities API (introduced in WordPress 6.9).

| Subcommand | Description |
|---|---|
| `wp ability list` | Lists all registered abilities |
| `wp ability get` | Gets details of a specific ability |
| `wp ability run` | Executes a specific ability |
| `wp ability exists` | Checks if an ability exists |
| `wp ability can-run` | Checks if a user can run an ability |
| `wp ability validate` | Validates input before execution |

---

## 2. wp admin

Opens /wp-admin/ in a browser. **(no subcommands)**

---

## 3. wp block

Manages WordPress block editor blocks and related entities (new in WP-CLI 2.12.0 / WordPress 7.0 cycle).

| Subcommand | Description |
|---|---|
| `wp block list` | Lists registered block types |
| `wp block get` | Gets details about a block type |

*Note: The `wp block` command group is actively being developed. Additional subcommands for exporting patterns and templates are planned.*

---

## 4. wp cache

Adds, removes, fetches, and flushes the WP Object Cache object.

| Subcommand | Description |
|---|---|
| `wp cache add` | Adds a value to the object cache |
| `wp cache decr` | Decrements a numeric value in the object cache |
| `wp cache delete` | Removes a value from the object cache |
| `wp cache flush` | Flushes the object cache |
| `wp cache get` | Gets a value from the object cache |
| `wp cache incr` | Increments a numeric value in the object cache |
| `wp cache replace` | Replaces a value in the object cache |
| `wp cache set` | Sets a value to the object cache |
| `wp cache supports` | Checks if the object cache supports a feature |
| `wp cache type` | Attempts to determine the object cache type |

---

## 5. wp cap

Adds, removes, and lists capabilities of a user role.

| Subcommand | Description |
|---|---|
| `wp cap add` | Adds capabilities to a given role |
| `wp cap list` | Lists capabilities for a given role |
| `wp cap remove` | Removes capabilities from a given role |

---

## 6. wp cli

Reviews current WP-CLI info, checks for updates, or views defined aliases.

| Subcommand | Description |
|---|---|
| `wp cli alias` | Retrieves, sets, and updates aliases for WP-CLI commands |
| `wp cli cache` | Manages the internal WP-CLI cache |
| `wp cli check-update` | Checks for WP-CLI updates |
| `wp cli cmd-dump` | Dumps the list of installed commands in JSON format |
| `wp cli completions` | Generates tab completion strings |
| `wp cli has-command` | Detects if a command exists |
| `wp cli info` | Prints various details about the WP-CLI environment |
| `wp cli param-dump` | Dumps the list of global parameters in JSON format |
| `wp cli update` | Updates WP-CLI to the latest release |
| `wp cli version` | Prints the WP-CLI version |

### wp cli alias (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp cli alias add` | Creates an alias |
| `wp cli alias delete` | Deletes an alias |
| `wp cli alias get` | Gets the value for an alias |
| `wp cli alias is-group` | Checks if an alias is a group |
| `wp cli alias list` | Lists available WP-CLI aliases |
| `wp cli alias update` | Updates an alias |

### wp cli cache (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp cli cache clear` | Clears the internal cache |
| `wp cli cache prune` | Prunes the internal cache |

---

## 7. wp comment

Creates, updates, deletes, and moderates comments.

| Subcommand | Description |
|---|---|
| `wp comment approve` | Approves a comment |
| `wp comment count` | Counts comments, on whole blog or on a given post |
| `wp comment create` | Creates a new comment |
| `wp comment delete` | Deletes a comment |
| `wp comment exists` | Verifies whether a comment exists |
| `wp comment generate` | Generates some number of new dummy comments |
| `wp comment get` | Gets the data of a single comment |
| `wp comment list` | Gets a list of comments |
| `wp comment meta` | Adds, updates, deletes, and lists comment custom fields |
| `wp comment recount` | Recalculates the comment_count value for one or more posts |
| `wp comment spam` | Marks a comment as spam |
| `wp comment status` | Gets the status of a comment |
| `wp comment trash` | Trashes a comment |
| `wp comment unapprove` | Unapproves a comment |
| `wp comment unspam` | Unmarks a comment as spam |
| `wp comment untrash` | Untrashes a comment |
| `wp comment update` | Updates one or more comments |

### wp comment meta (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp comment meta add` | Adds a meta field |
| `wp comment meta delete` | Deletes a meta field |
| `wp comment meta get` | Gets a meta field value |
| `wp comment meta list` | Lists all meta fields |
| `wp comment meta patch` | Updates a nested value for a meta field |
| `wp comment meta pluck` | Gets a nested value from a meta field |
| `wp comment meta update` | Updates a meta field |

---

## 8. wp config

Generates and reads the wp-config.php file.

| Subcommand | Description |
|---|---|
| `wp config create` | Generates a wp-config.php file |
| `wp config delete` | Deletes a specific constant or variable from wp-config.php |
| `wp config edit` | Launches system editor to edit the wp-config.php file |
| `wp config get` | Gets the value of a specific constant or variable from wp-config.php |
| `wp config has` | Checks whether a specific constant or variable exists in wp-config.php |
| `wp config is-true` | Checks whether a specific constant or variable is truthy |
| `wp config list` | Lists variables, constants, and includes defined in wp-config.php |
| `wp config path` | Gets the path to wp-config.php |
| `wp config set` | Sets the value of a specific constant or variable in wp-config.php |
| `wp config shuffle-salts` | Refreshes the salts defined in wp-config.php |

---

## 9. wp core

Downloads, installs, updates, and manages a WordPress installation.

| Subcommand | Description |
|---|---|
| `wp core check-update` | Checks for WordPress updates via version API |
| `wp core download` | Downloads core WordPress files |
| `wp core install` | Runs the standard WordPress installation process |
| `wp core is-installed` | Checks if WordPress is installed |
| `wp core multisite-convert` | Transforms a single-site install into a multisite install |
| `wp core multisite-install` | Installs WordPress multisite from scratch |
| `wp core update` | Updates WordPress to a newer version |
| `wp core update-db` | Runs the WordPress database update procedure |
| `wp core verify-checksums` | Verifies WordPress files against checksums |
| `wp core version` | Displays the WordPress version |

---

## 10. wp cron

Tests, runs, and deletes WP-Cron events; manages WP-Cron schedules.

| Subcommand | Description |
|---|---|
| `wp cron event` | Schedules, runs, and deletes WP-Cron events |
| `wp cron schedule` | Gets WP-Cron schedules |
| `wp cron test` | Tests the WP-Cron spawning system |

### wp cron event (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp cron event delete` | Deletes the next scheduled cron event for the given hook |
| `wp cron event list` | Lists scheduled cron events |
| `wp cron event run` | Runs the next scheduled cron event for the given hook |
| `wp cron event schedule` | Schedules a new cron event |
| `wp cron event unschedule` | Unschedules all cron events for a given hook |

### wp cron schedule (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp cron schedule list` | Lists available cron schedules |

---

## 11. wp db

Performs basic database operations using credentials stored in wp-config.php.

| Subcommand | Description |
|---|---|
| `wp db check` | Checks the current status of the database |
| `wp db clean` | Removes all tables from the database |
| `wp db cli` | Opens a MySQL console using credentials from wp-config.php |
| `wp db columns` | Displays information about a given table |
| `wp db create` | Creates a new database |
| `wp db drop` | Deletes the existing database |
| `wp db export` | Exports the database to a file or to STDOUT |
| `wp db import` | Imports a database from a file or from STDIN |
| `wp db optimize` | Optimizes the database |
| `wp db prefix` | Displays the database table prefix |
| `wp db query` | Executes a SQL query against the database |
| `wp db repair` | Repairs the database |
| `wp db reset` | Removes all tables with the `$table_prefix` from the database |
| `wp db search` | Finds a string in the database |
| `wp db size` | Displays the database name and size |
| `wp db tables` | Lists the database tables |

---

## 12. wp dist-archive

Creates a distribution archive based on a project's .distignore file. **(no subcommands)**

---

## 13. wp embed

Inspects oEmbed providers, clears embed cache, and more.

| Subcommand | Description |
|---|---|
| `wp embed cache` | Finds, triggers, and deletes oEmbed caches |
| `wp embed fetch` | Attempts to convert a URL into embed HTML |
| `wp embed handler` | Retrieves embed handlers |
| `wp embed provider` | Retrieves oEmbed providers |

### wp embed cache (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp embed cache clear` | Deletes all oEmbed caches for a given post |
| `wp embed cache find` | Finds an oEmbed cache post ID for a given URL |
| `wp embed cache trigger` | Triggers a caching of all oEmbed results for a given post |

### wp embed handler (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp embed handler list` | Lists all available embed handlers |

### wp embed provider (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp embed provider list` | Lists all available oEmbed providers |
| `wp embed provider match` | Gets the matching provider for a given URL |

---

## 14. wp eval

Executes arbitrary PHP code. **(no subcommands)**

---

## 15. wp eval-file

Loads and executes a PHP file. **(no subcommands)**

---

## 16. wp export

Exports WordPress content to a WXR file. **(no subcommands)**

---

## 17. wp find

Finds WordPress installations on the filesystem. **(no subcommands)**

---

## 18. wp help

Gets help on WP-CLI, or on a specific command. **(no subcommands)**

---

## 19. wp i18n

Provides internationalization tools for WordPress projects.

| Subcommand | Description |
|---|---|
| `wp i18n make-json` | Extracts strings from PO files and adds them to individual JSON files |
| `wp i18n make-mo` | Creates MO files from PO files |
| `wp i18n make-php` | Creates PHP files from PO files |
| `wp i18n make-pot` | Creates a POT file for a WordPress project |
| `wp i18n update-po` | Updates PO files from a POT file |

---

## 20. wp import

Imports content from a given WXR file. **(no subcommands)**

---

## 21. wp language

Installs, activates, and manages language packs.

| Subcommand | Description |
|---|---|
| `wp language core` | Manages core language packs |
| `wp language plugin` | Manages plugin language packs |
| `wp language theme` | Manages theme language packs |

### wp language core (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp language core activate` | Activates a given language |
| `wp language core install` | Installs a given language |
| `wp language core is-installed` | Checks if a given language is installed |
| `wp language core list` | Lists all available languages |
| `wp language core uninstall` | Uninstalls a given language |
| `wp language core update` | Updates installed languages |

### wp language plugin (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp language plugin install` | Installs a given language for a plugin |
| `wp language plugin is-installed` | Checks if a given language is installed for a plugin |
| `wp language plugin list` | Lists all available languages for one or more plugins |
| `wp language plugin uninstall` | Uninstalls a given language for a plugin |
| `wp language plugin update` | Updates installed languages for one or more plugins |

### wp language theme (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp language theme install` | Installs a given language for a theme |
| `wp language theme is-installed` | Checks if a given language is installed for a theme |
| `wp language theme list` | Lists all available languages for one or more themes |
| `wp language theme uninstall` | Uninstalls a given language for a theme |
| `wp language theme update` | Updates installed languages for one or more themes |

---

## 22. wp maintenance-mode

Activates, deactivates, or checks the status of the maintenance mode of a site.

| Subcommand | Description |
|---|---|
| `wp maintenance-mode activate` | Activates maintenance mode |
| `wp maintenance-mode deactivate` | Deactivates maintenance mode |
| `wp maintenance-mode is-active` | Detects maintenance mode status |
| `wp maintenance-mode status` | Displays maintenance mode status |

---

## 23. wp media

Imports files as attachments, regenerates thumbnails, or lists registered image sizes.

| Subcommand | Description |
|---|---|
| `wp media fix-orientation` | Fixes the orientation of one or more images |
| `wp media image-size` | Lists image sizes registered with WordPress |
| `wp media import` | Creates attachments from local files or URLs |
| `wp media regenerate` | Regenerates thumbnails for one or more attachments |

---

## 24. wp menu

Lists, creates, assigns, and deletes the active theme's navigation menus.

| Subcommand | Description |
|---|---|
| `wp menu create` | Creates a new menu |
| `wp menu delete` | Deletes one or more menus |
| `wp menu item` | Lists, adds, and deletes items for a menu |
| `wp menu list` | Gets a list of menus |
| `wp menu location` | Assigns, removes, and lists menu locations |

### wp menu item (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp menu item add-custom` | Adds a custom menu item |
| `wp menu item add-post` | Adds a post as a menu item |
| `wp menu item add-term` | Adds a taxonomy term as a menu item |
| `wp menu item delete` | Deletes one or more items from a menu |
| `wp menu item list` | Gets a list of items associated with a menu |
| `wp menu item update` | Updates a menu item |

### wp menu location (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp menu location assign` | Assigns a menu to a location |
| `wp menu location list` | Lists locations for the current theme |
| `wp menu location remove` | Removes a menu from a location |

---

## 25. wp network

Performs network-wide operations.

| Subcommand | Description |
|---|---|
| `wp network meta` | Gets, adds, updates, deletes, and lists network custom fields |

### wp network meta (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp network meta add` | Adds a meta field |
| `wp network meta delete` | Deletes a meta field |
| `wp network meta get` | Gets a meta field value |
| `wp network meta list` | Lists all meta fields |
| `wp network meta patch` | Updates a nested value for a meta field |
| `wp network meta pluck` | Gets a nested value from a meta field |
| `wp network meta update` | Updates a meta field |

---

## 26. wp option

Retrieves and sets site options, including plugin and WordPress settings.

| Subcommand | Description |
|---|---|
| `wp option add` | Adds a new option value |
| `wp option delete` | Deletes an option |
| `wp option get` | Gets the value of an option |
| `wp option list` | Lists options and their values |
| `wp option patch` | Updates a nested value in an option |
| `wp option pluck` | Gets a nested value from an option |
| `wp option set` | Alias for `wp option update` |
| `wp option update` | Updates an option value |

---

## 27. wp package

Lists, installs, and removes WP-CLI packages.

| Subcommand | Description |
|---|---|
| `wp package browse` | Browses WP-CLI packages available for installation |
| `wp package install` | Installs a WP-CLI package |
| `wp package list` | Lists installed WP-CLI packages |
| `wp package path` | Gets the path to an installed WP-CLI package |
| `wp package uninstall` | Uninstalls a WP-CLI package |
| `wp package update` | Updates all installed WP-CLI packages |

---

## 28. wp plugin

Manages plugins, including installs, activations, and updates.

| Subcommand | Description |
|---|---|
| `wp plugin activate` | Activates one or more plugins |
| `wp plugin auto-updates` | Manages plugin auto-updates |
| `wp plugin deactivate` | Deactivates one or more plugins |
| `wp plugin delete` | Deletes plugin files without deactivating or uninstalling |
| `wp plugin get` | Gets details about an installed plugin |
| `wp plugin install` | Installs one or more plugins |
| `wp plugin is-active` | Checks if a given plugin is active |
| `wp plugin is-installed` | Checks if a given plugin is installed |
| `wp plugin list` | Gets a list of plugins |
| `wp plugin path` | Gets the path to a plugin or to the plugin directory |
| `wp plugin search` | Searches the WordPress.org plugin directory |
| `wp plugin status` | Reveals the status of one or all plugins |
| `wp plugin toggle` | Toggles a plugin's activation state |
| `wp plugin uninstall` | Uninstalls one or more plugins |
| `wp plugin update` | Updates one or more plugins |
| `wp plugin verify-checksums` | Verifies plugin files against checksums |

### wp plugin auto-updates (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp plugin auto-updates disable` | Disables the auto-updates for a plugin |
| `wp plugin auto-updates enable` | Enables the auto-updates for a plugin |
| `wp plugin auto-updates status` | Shows the status of auto-updates for a plugin |

---

## 29. wp post

Manages posts, content, and meta.

| Subcommand | Description |
|---|---|
| `wp post create` | Creates a new post |
| `wp post delete` | Deletes an existing post |
| `wp post edit` | Launches system editor to edit post content |
| `wp post exists` | Verifies whether a post exists |
| `wp post generate` | Generates some posts |
| `wp post get` | Gets details about a post |
| `wp post list` | Gets a list of posts |
| `wp post meta` | Adds, updates, deletes, and lists post custom fields |
| `wp post term` | Adds, updates, removes, and lists post terms |
| `wp post update` | Updates one or more existing posts |
| `wp post url-to-id` | Gets the post ID for a given URL |

### wp post meta (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp post meta add` | Adds a meta field |
| `wp post meta delete` | Deletes a meta field |
| `wp post meta get` | Gets a meta field value |
| `wp post meta list` | Lists all meta fields |
| `wp post meta patch` | Updates a nested value for a meta field |
| `wp post meta pluck` | Gets a nested value from a meta field |
| `wp post meta update` | Updates a meta field |

### wp post term (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp post term add` | Adds a term to a post |
| `wp post term list` | Lists terms associated with a post |
| `wp post term remove` | Removes a term from a post |
| `wp post term set` | Sets the terms for a post |

---

## 30. wp post-type

Retrieves details on the site's registered post types.

| Subcommand | Description |
|---|---|
| `wp post-type get` | Gets details about a registered post type |
| `wp post-type list` | Lists registered post types |

---

## 31. wp profile

Quickly identifies what's slow with WordPress.

| Subcommand | Description |
|---|---|
| `wp profile eval` | Profiles arbitrary code execution |
| `wp profile eval-file` | Profiles execution of an arbitrary file |
| `wp profile hook` | Profiles a specific WordPress hook |
| `wp profile stage` | Profiles each stage of the WordPress load process |

---

## 32. wp rewrite

Lists or flushes the site's rewrite rules, updates the permalink structure.

| Subcommand | Description |
|---|---|
| `wp rewrite flush` | Flushes rewrite rules |
| `wp rewrite list` | Gets a list of the current rewrite rules |
| `wp rewrite structure` | Updates the permalink structure |

---

## 33. wp role

Manages user roles, including creating new roles and resetting to defaults.

| Subcommand | Description |
|---|---|
| `wp role create` | Creates a new role |
| `wp role delete` | Deletes an existing role |
| `wp role exists` | Checks if a role exists |
| `wp role list` | Lists all roles |
| `wp role reset` | Resets any default role to default capabilities |

---

## 34. wp scaffold

Generates code for post types, taxonomies, plugins, child themes, etc.

| Subcommand | Description |
|---|---|
| `wp scaffold _s` | Generates starter code for a theme based on _s |
| `wp scaffold block` | Generates PHP, JS, and CSS code for registering a Gutenberg block |
| `wp scaffold child-theme` | Generates child theme based on an existing theme |
| `wp scaffold plugin` | Generates starter files for a plugin |
| `wp scaffold plugin-tests` | Generates test files for a plugin |
| `wp scaffold post-type` | Generates PHP code for registering a custom post type |
| `wp scaffold taxonomy` | Generates PHP code for registering a custom taxonomy |
| `wp scaffold theme-tests` | Generates test files for a theme |

---

## 35. wp search-replace

Searches/replaces strings in the database. **(no subcommands)**

---

## 36. wp server

Launches PHP's built-in web server for a specific WordPress installation. **(no subcommands)**

---

## 37. wp shell

Opens an interactive PHP console for running and testing PHP code. **(no subcommands)**

---

## 38. wp sidebar

Lists registered sidebars.

| Subcommand | Description |
|---|---|
| `wp sidebar list` | Lists registered sidebars |

---

## 39. wp site

Creates, deletes, empties, moderates, and lists one or more sites on a multisite installation.

| Subcommand | Description |
|---|---|
| `wp site activate` | Activates one or more sites |
| `wp site archive` | Archives one or more sites |
| `wp site create` | Creates a site in a multisite installation |
| `wp site deactivate` | Deactivates one or more sites |
| `wp site delete` | Deletes a site in a multisite installation |
| `wp site empty` | Empties a site of its content |
| `wp site list` | Lists all sites in a multisite installation |
| `wp site mature` | Sets one or more sites as mature |
| `wp site meta` | Adds, updates, deletes, and lists site custom fields |
| `wp site option` | Adds, updates, deletes, and lists site options |
| `wp site private` | Sets one or more sites as private |
| `wp site public` | Sets one or more sites as public |
| `wp site spam` | Marks one or more sites as spam |
| `wp site switch-language` | Activates a given language for a site |
| `wp site unarchive` | Unarchives one or more sites |
| `wp site unmature` | Sets one or more sites as unmature |
| `wp site unspam` | Removes one or more sites from spam |

### wp site meta (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp site meta add` | Adds a meta field |
| `wp site meta delete` | Deletes a meta field |
| `wp site meta get` | Gets a meta field value |
| `wp site meta list` | Lists all meta fields |
| `wp site meta patch` | Updates a nested value for a meta field |
| `wp site meta pluck` | Gets a nested value from a meta field |
| `wp site meta update` | Updates a meta field |

### wp site option (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp site option add` | Adds a site option |
| `wp site option delete` | Deletes a site option |
| `wp site option get` | Gets a site option |
| `wp site option list` | Lists site options |
| `wp site option patch` | Updates a nested value in a site option |
| `wp site option pluck` | Gets a nested value from a site option |
| `wp site option update` | Updates a site option |

---

## 40. wp super-admin

Lists, adds, or removes super admin users on a multisite installation.

| Subcommand | Description |
|---|---|
| `wp super-admin add` | Grants super admin privileges to one or more users |
| `wp super-admin list` | Lists all super admins |
| `wp super-admin remove` | Removes super admin privileges from one or more users |

---

## 41. wp taxonomy

Retrieves information about registered taxonomies.

| Subcommand | Description |
|---|---|
| `wp taxonomy get` | Gets details about a registered taxonomy |
| `wp taxonomy list` | Lists registered taxonomies |

---

## 42. wp term

Manages taxonomy terms and term meta, with create, delete, and list commands.

| Subcommand | Description |
|---|---|
| `wp term create` | Creates a new term |
| `wp term delete` | Deletes an existing term |
| `wp term generate` | Generates some terms |
| `wp term get` | Gets details about a term |
| `wp term list` | Lists terms in a taxonomy |
| `wp term meta` | Adds, updates, deletes, and lists term custom fields |
| `wp term migrate` | Migrates a term to a new taxonomy |
| `wp term recount` | Recalculates the number of posts for one or more terms |
| `wp term update` | Updates an existing term |

### wp term meta (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp term meta add` | Adds a meta field |
| `wp term meta delete` | Deletes a meta field |
| `wp term meta get` | Gets a meta field value |
| `wp term meta list` | Lists all meta fields |
| `wp term meta patch` | Updates a nested value for a meta field |
| `wp term meta pluck` | Gets a nested value from a meta field |
| `wp term meta update` | Updates a meta field |

---

## 43. wp theme

Manages themes, including installs, activations, and updates.

| Subcommand | Description |
|---|---|
| `wp theme activate` | Activates a theme |
| `wp theme auto-updates` | Manages theme auto-updates |
| `wp theme delete` | Deletes one or more themes |
| `wp theme disable` | Disables a theme on a WordPress multisite install |
| `wp theme enable` | Enables a theme on a WordPress multisite install |
| `wp theme get` | Gets details about an installed theme |
| `wp theme install` | Installs one or more themes |
| `wp theme is-active` | Checks if a given theme is active |
| `wp theme is-installed` | Checks if a given theme is installed |
| `wp theme list` | Gets a list of themes |
| `wp theme mod` | Sets, gets, and removes theme mods |
| `wp theme path` | Gets the path to a theme or to the theme directory |
| `wp theme search` | Searches the WordPress.org theme directory |
| `wp theme status` | Reveals the status of one or all themes |
| `wp theme update` | Updates one or more themes |

### wp theme auto-updates (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp theme auto-updates disable` | Disables the auto-updates for a theme |
| `wp theme auto-updates enable` | Enables the auto-updates for a theme |
| `wp theme auto-updates status` | Shows the status of auto-updates for a theme |

### wp theme mod (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp theme mod get` | Gets one or more theme mods |
| `wp theme mod list` | Gets a list of theme mods |
| `wp theme mod remove` | Removes one or more theme mods |
| `wp theme mod set` | Sets the value of a theme mod |

---

## 44. wp transient

Adds, gets, and deletes entries in the WordPress Transient Cache.

| Subcommand | Description |
|---|---|
| `wp transient delete` | Deletes a transient value |
| `wp transient get` | Gets a transient value |
| `wp transient list` | Lists transients and their values |
| `wp transient set` | Sets a transient value |
| `wp transient type` | Determines the type of transients implementation |

---

## 45. wp user

Manages users, along with their roles, capabilities, and meta.

| Subcommand | Description |
|---|---|
| `wp user add-cap` | Adds a capability to a user |
| `wp user add-role` | Adds a role for a user |
| `wp user application-password` | Creates, updates, deletes, lists, and retrieves application passwords |
| `wp user check-password` | Checks if a user's password is valid or not |
| `wp user create` | Creates a new user |
| `wp user delete` | Deletes one or more users from the current site |
| `wp user exists` | Verifies whether a user exists |
| `wp user generate` | Generates some users |
| `wp user get` | Gets details about a user |
| `wp user import-csv` | Imports users from a CSV file |
| `wp user list` | Lists users |
| `wp user list-caps` | Lists all capabilities for a user |
| `wp user meta` | Adds, updates, deletes, and lists user custom fields |
| `wp user remove-cap` | Removes a user's capability |
| `wp user remove-role` | Removes a user's role |
| `wp user reset-password` | Resets the password for one or more users |
| `wp user session` | Destroys and lists a user's sessions |
| `wp user set-role` | Sets the user role |
| `wp user signup` | Manages signups on a multisite installation |
| `wp user spam` | Marks one or more users as spam on multisite |
| `wp user term` | Adds, updates, removes, and lists user terms |
| `wp user unspam` | Removes one or more users from spam on multisite |
| `wp user update` | Updates an existing user |

### wp user application-password (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp user application-password create` | Creates a new application password |
| `wp user application-password delete` | Deletes an existing application password |
| `wp user application-password exists` | Checks whether an application password exists |
| `wp user application-password get` | Gets a specific application password |
| `wp user application-password list` | Lists all application passwords for a user |
| `wp user application-password update` | Updates an existing application password |

### wp user meta (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp user meta add` | Adds a meta field |
| `wp user meta delete` | Deletes a meta field |
| `wp user meta get` | Gets a meta field value |
| `wp user meta list` | Lists all meta fields |
| `wp user meta patch` | Updates a nested value for a meta field |
| `wp user meta pluck` | Gets a nested value from a meta field |
| `wp user meta update` | Updates a meta field |

### wp user session (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp user session destroy` | Destroys a session for the given user |
| `wp user session list` | Lists sessions for the given user |

### wp user signup (nested subcommands)

| Subcommand | Description |
|---|---|
| `wp user signup activate` | Activates a signup |
| `wp user signup delete` | Deletes a signup |
| `wp user signup list` | Lists signups |

---

## 46. wp widget

Manages widgets, including adding and moving them within sidebars.

| Subcommand | Description |
|---|---|
| `wp widget add` | Adds a widget to a sidebar |
| `wp widget deactivate` | Deactivates one or more widgets from a sidebar |
| `wp widget delete` | Deletes one or more widgets from a sidebar |
| `wp widget list` | Lists widgets associated with a sidebar |
| `wp widget move` | Moves a widget within or between sidebars |
| `wp widget reset` | Resets a sidebar |
| `wp widget update` | Updates options for an existing widget |

---

## Summary statistics

| Metric | Count |
|---|---|
| Top-level command groups | 46 |
| Standalone commands (no subcommands) | 7 |
| Command groups with subcommands | 39 |
| Total subcommands (all levels) | ~280+ |

### Top-level command groups by category

**Content management:** post, comment, media, menu, term, widget, sidebar, embed
**User management:** user, cap, role, super-admin
**Site configuration:** option, config, rewrite, transient, cache, maintenance-mode
**Plugin/theme management:** plugin, theme
**Core management:** core, db, search-replace, language
**Taxonomy/post-type introspection:** taxonomy, post-type
**Multisite:** site, network
**Development/tooling:** scaffold, i18n, profile, eval, eval-file, shell, server, find, export, import, dist-archive
**WP-CLI self-management:** cli, package, help
**WordPress 6.9+ features:** ability, block
