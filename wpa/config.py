"""Site configuration management for WPA."""

import getpass
import ipaddress
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

SITE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*$")
PRIVATE_HOSTNAMES = {"localhost"}
PRIVATE_TLDS = {".lan", ".local", ".test", ".internal"}


def is_private_url(url):
    """Check if a URL points to a private/LAN or loopback address.

    Returns True for RFC 1918 private IPs, loopback IPs, 'localhost',
    and hostnames ending in private TLDs (.lan, .local, .test, .internal).
    Returns False for public IPs and unrecognized hostnames.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in PRIVATE_HOSTNAMES:
        return True

    if any(hostname.endswith(tld) for tld in PRIVATE_TLDS):
        return True

    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback
    except ValueError:
        return False


def get_config_dir():
    """Return the WPA config directory, respecting XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        return Path(xdg) / "wpa"
    return Path.home() / ".config" / "wpa"


def list_sites():
    """Return sorted list of site names that have .env files."""
    config_dir = get_config_dir()
    if not config_dir.exists():
        return []
    return sorted(
        d.name for d in config_dir.iterdir() if d.is_dir() and (d / ".env").exists()
    )


def validate_site_name(name):
    """Validate site name is filesystem-safe (alphanumeric + hyphens)."""
    return bool(name and SITE_NAME_PATTERN.match(name))


def create_site_config(site_name=None):
    """Interactively create a new site configuration.

    Returns the path to the created .env file, or None if cancelled.
    """
    if site_name is None:
        site_name = input("Site name: ").strip()

    if not validate_site_name(site_name):
        print(
            f"Error: Invalid site name '{site_name}'. Use alphanumeric characters and hyphens only."
        )
        sys.exit(1)

    config_dir = get_config_dir()
    site_dir = config_dir / site_name

    if site_dir.exists() and (site_dir / ".env").exists():
        confirm = (
            input(f"Config '{site_name}' already exists. Overwrite? [y/N]: ")
            .strip()
            .lower()
        )
        if confirm != "y":
            print("Cancelled.")
            sys.exit(0)

    # Gather credentials
    while True:
        site_url = input("WP_SITE_URL: ").strip()
        if site_url.startswith("https://"):
            break
        if site_url.startswith("http://") and is_private_url(site_url):
            print(
                "Warning: Using HTTP on a private/LAN address."
                " Credentials are not encrypted in transit."
            )
            break
        print(
            "Error: URL must start with https:// (HTTP allowed only for private/LAN addresses)"
        )

    wp_user = input("WP_USER: ").strip()
    if not wp_user:
        print("Error: WP_USER cannot be empty.")
        sys.exit(1)

    wp_password = getpass.getpass("WP_APP_PASSWORD: ")
    if not wp_password:
        print("Error: WP_APP_PASSWORD cannot be empty.")
        sys.exit(1)

    admin_path = input("WP_ADMIN_PATH (default: wp-admin): ").strip()
    if not admin_path:
        admin_path = "wp-admin"

    # Write config
    site_dir.mkdir(parents=True, exist_ok=True)
    env_path = site_dir / ".env"
    env_path.write_text(
        f"WP_SITE_URL={site_url}\n"
        f"WP_USER={wp_user}\n"
        f"WP_APP_PASSWORD={wp_password}\n"
        f"WP_ADMIN_PATH={admin_path}\n"
    )
    env_path.chmod(0o600)
    print(f"\nSaved to {env_path}")
    return env_path


def migrate_repo_env():
    """Offer to migrate repo-root .env to XDG config dir.

    Returns the path to the migrated .env, or None if user declines.
    """
    repo_env = Path(__file__).parent.parent / ".env"
    if not repo_env.exists():
        return None

    sites = list_sites()
    if sites:
        return None  # Already have XDG configs, don't offer migration

    print(f"Found repo-root config at {repo_env}")
    site_name = input(
        "Migrate to XDG config? Enter site name (or press Enter to skip): "
    ).strip()
    if not site_name:
        return None

    if not validate_site_name(site_name):
        print(
            f"Error: Invalid site name '{site_name}'. Use alphanumeric characters and hyphens only."
        )
        return None

    config_dir = get_config_dir()
    site_dir = config_dir / site_name
    site_dir.mkdir(parents=True, exist_ok=True)

    dest = site_dir / ".env"
    dest.write_text(repo_env.read_text())
    dest.chmod(0o600)

    # Add WP_ADMIN_PATH if not present
    content = dest.read_text()
    if "WP_ADMIN_PATH" not in content:
        with open(dest, "a") as f:
            f.write("WP_ADMIN_PATH=wp-admin\n")

    print(f"Migrated to {dest}")

    delete = input(f"Delete {repo_env}? [y/N]: ").strip().lower()
    if delete == "y":
        repo_env.unlink()
        print(f"Deleted {repo_env}")

    return dest


def resolve_config(site_name=None):
    """Resolve which site config to use.

    Returns (site_url, user, password, admin_path) or exits on failure.
    """
    sites = list_sites()

    if site_name:
        # Explicit --site: no prompts
        config_dir = get_config_dir()
        env_path = config_dir / site_name / ".env"
        if not env_path.exists():
            print(f"Error: No config found for site '{site_name}'.")
            available = list_sites()
            if available:
                print(f"Available sites: {', '.join(available)}")
            sys.exit(1)
        return _load_env(env_path)

    if len(sites) == 0:
        # No configs — try migration, then create
        env_path = migrate_repo_env()
        if env_path:
            return _load_env(env_path)

        print("No site configs found. Let's create one.")
        env_path = create_site_config()
        return _load_env(env_path)

    if len(sites) == 1:
        # Single config — use automatically
        config_dir = get_config_dir()
        env_path = config_dir / sites[0] / ".env"
        print(f"Using site: {sites[0]}")
        return _load_env(env_path)

    # Multiple configs — prompt to select
    print("Available sites:")
    for i, name in enumerate(sites, 1):
        print(f"  {i}. {name}")

    while True:
        choice = input("Select site number: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sites):
                config_dir = get_config_dir()
                env_path = config_dir / sites[idx] / ".env"
                return _load_env(env_path)
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(sites)}.")


def _load_env(env_path):
    """Load config from a specific .env file path.

    Returns (site_url, user, password, admin_path).
    """
    load_dotenv(env_path, override=True)

    site_url = os.environ.get("WP_SITE_URL", "")
    user = os.environ.get("WP_USER", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    admin_path = os.environ.get("WP_ADMIN_PATH", "wp-admin")

    if not all([site_url, user, password]):
        print(
            f"Error: WP_SITE_URL, WP_USER, and WP_APP_PASSWORD must all be set in {env_path}"
        )
        sys.exit(1)

    if not site_url.startswith("https://"):
        if site_url.startswith("http://") and is_private_url(site_url):
            print(
                "Warning: Using HTTP on a private/LAN address."
                " Credentials are not encrypted in transit."
            )
        else:
            print(
                "Error: WP_SITE_URL must use HTTPS to protect credentials in transit."
            )
            sys.exit(1)

    return site_url.rstrip("/"), user, password, admin_path
