# WAF Compatibility

WordPress security plugins with a Web Application Firewall (WAF) — most
commonly **Wordfence** — intercept some requests before they reach WordPress.
The WAF answers with an **HTML error page**, not a WordPress JSON error, which
is how WPA distinguishes a WAF block from a real API error: WordPress itself
always returns JSON from `/wp-json/` endpoints.

Since v0.8.1, WPA detects this signature (HTML body + HTTP 403/404/406/429/503
from a REST endpoint) and reports it as a **possible WAF block** with a
pointer to this document, instead of dumping the raw HTML.

WPA deliberately does **not** try to work around a WAF by re-encoding
parameters or switching request methods. WAF rules like author-enumeration
protection exist for good reasons; the fixes below are site-configuration
changes made by the site admin, not bypasses. See
[#40](https://github.com/cadentdev/wpa/issues/40) for the policy discussion.

## Known symptoms

| Symptom | HTTP | Cause | Affected commands |
|---|---|---|---|
| `DELETE` blocked | 403 (HTML) | Wordfence WAF blocks the DELETE method | `user delete`, `post delete`, `page delete`, `media delete`, `comment delete`, `term delete` |
| `?author=` blocked | 404 (HTML) | Wordfence author-enumeration protection | `post list --author` ([#25](https://github.com/cadentdev/wpa/issues/25)) |
| `wp-login.php` POST rejected | varies | Login security / rate limiting | `user create --send-email` |
| Application Passwords disabled | 401 (JSON) | Wordfence disables them by default | all commands (see GETTING-STARTED.md) |

## Fixes (site admin)

All paths are in **wp-admin → Wordfence**; equivalent settings exist in other
security plugins.

- **DELETE blocked:** Firewall → All Firewall Options → Whitelisted URLs — add
  the affected endpoint prefix (e.g. `/wp-json/wp/v2/users/`). On staging
  sites, Learning Mode also works.
- **`?author=` blocked:** the protection can be disabled under Firewall
  options ("Prevent discovery of usernames..."), but consider leaving it on —
  it protects against unauthenticated username mapping. Workaround: list
  without `--author` and filter client-side (e.g. with `--format json` and
  `jq 'map(select(.author == 8))'`).
- **`--send-email` rejected:** check Login Security rate limits for
  `wp-login.php`. WPA warns when WordPress does not confirm the request.

## Client-side workarounds under consideration

A client-side `--author` fallback (fetch unfiltered, filter locally, warn that
server-side filtering was unavailable) is tracked in
[#25](https://github.com/cadentdev/wpa/issues/25). Constraint: WPA must not
retry with re-encoded `?author=` parameters or otherwise defeat the WAF rule.
