# Getting Started with WPA

This guide walks through setting up a WordPress site to work with WPA, from verifying the REST API to running your first command.

## Prerequisites

- Python 3.9+
- A WordPress site (5.6+ for Application Passwords)
- An Administrator account on the site

## Step 1: Verify the REST API is accessible

The WordPress REST API must be reachable. Test from any machine that can reach your site:

```bash
curl -s -o /dev/null -w "HTTP: %{http_code}\n" https://example.com/wp-json/wp/v2/
```

**Expected:** `HTTP: 200`

If you get a 200, check that the users endpoint exists:

```bash
curl -s https://example.com/wp-json/wp/v2/ | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Namespace: {d.get(\"namespace\", \"?\")}')
print(f'Routes: {len(d.get(\"routes\", {}))} endpoints')
print(f'Users endpoint: {\"/wp/v2/users\" in str(d.get(\"routes\", {}))}')
"
```

**Expected:** Namespace `wp/v2`, 100+ routes, Users endpoint `True`.

### Troubleshooting

| Response | Cause | Fix |
|----------|-------|-----|
| 404 | Pretty permalinks not enabled | Settings → Permalinks → select any option except "Plain" |
| 301/302 | HTTP → HTTPS redirect | Use `https://` in your URL |
| 403 | REST API disabled by plugin | Check security plugin settings (see Wordfence section below) |
| Connection refused | Site not reachable | Check URL, DNS, firewall |

## Step 2: Enable Application Passwords

Application Passwords are built into WordPress 5.6+ and provide a safe way to authenticate API requests without exposing your main password.

1. Log into **wp-admin**
2. Go to **Users → Profile** (or edit your admin user)
3. Scroll down to the **Application Passwords** section
4. Enter a name (e.g., "wpa-cli") and click **Add New Application Password**
5. Copy the generated password immediately — it won't be shown again

The generated password will look like `abcd EFGH 1234 ijkl MNOP 5678`. The spaces are cosmetic — WordPress strips them during authentication.

### Wordfence and Application Passwords

**Wordfence** (a popular WordPress security plugin) **disables Application Passwords by default**. If you don't see the Application Passwords section on your profile page, or if authentication returns 401 errors despite correct credentials:

1. Go to **Wordfence → All Options** (or Wordfence → Dashboard → All Options)
2. Search for **"Application Passwords"** or navigate to **Login Security → Settings**
3. Find the option **"Disable WordPress application passwords"**
4. **Uncheck** this option
5. Click **Save Changes**

After re-enabling, the Application Passwords section will appear on the Users → Profile page.

Other security plugins that may block Application Passwords:
- **iThemes Security** — check Security → Settings → WordPress Tweaks
- **Solid Security** — check Settings → Advanced
- **Custom security hardening** — check for filters on `wp_is_application_passwords_available`

## Step 3: Verify authentication

Test that your credentials work:

```bash
curl -s -u "USERNAME:APPPASSWORD" \
  https://example.com/wp-json/wp/v2/users/me?context=edit
```

**Expected:** JSON object with your user details (id, name, email, roles).

| Response | Cause | Fix |
|----------|-------|-----|
| 200 + JSON | Auth works | Proceed to step 4 |
| 401 | Bad credentials | Check username and app password; check Wordfence setting |
| 403 | Insufficient capabilities | User needs Administrator role |

To verify the full user list endpoint (requires `list_users` capability):

```bash
curl -s -u "USERNAME:APPPASSWORD" \
  https://example.com/wp-json/wp/v2/users?context=edit \
  | python3 -c "import sys,json; users=json.load(sys.stdin); print(f'{len(users)} users found')"
```

## Step 4: Configure WPA

```bash
wpa site add
```

You'll be prompted for:
- **Site name** — a short label (e.g., "mysite", "staging")
- **WP_SITE_URL** — full URL including `https://`
- **WP_USER** — your WordPress username
- **WP_APP_PASSWORD** — the application password from step 2 (input is hidden)
- **WP_ADMIN_PATH** — usually `wp-admin` (press Enter for default)

The config is stored at `~/.config/wpa/<site-name>/.env` with 600 permissions.

### HTTP sites (staging / LAN)

WPA enforces HTTPS for public addresses but allows HTTP for private/LAN addresses (RFC 1918, localhost, `.lan` domains). You'll see a warning:

```
Warning: Using HTTP on a private/LAN address. Credentials are not encrypted in transit.
```

This is expected for local staging environments.

## Step 5: Test with `wpa user list`

```bash
# List users (auto-selects site if only one config)
wpa user list

# Specify site
wpa user list --site staging

# Filter by role
wpa user list --role editor

# Different output formats
wpa user list --format json
wpa user list --format csv
wpa user list --format tsv

# Select specific fields
wpa user list --fields=id,username,email,roles
```

If this returns a table of users, everything is working. You're ready to use all WPA commands.

## Quick reference

```bash
# Site management
wpa site add                    # Create a new site config
wpa site list                   # List configured sites

# User management
wpa user list [--format FMT]    # List users
wpa user create --username X --email Y  # Create user
wpa user update ID --email Y    # Update user
wpa user delete ID --reassign Z # Delete user

# Page publishing
wpa publish page.md             # Publish markdown as WordPress page
```

See [README.md](README.md) for full documentation.
