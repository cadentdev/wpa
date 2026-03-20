"""Command-line interface for WPA — subcommand structure."""

import argparse
import getpass
import sys

from wpa import __version__
from wpa.config import create_site_config, list_sites, resolve_config
from wpa.formatter import format_output
from wpa.publish import parse_page, publish_page
from wpa.user import (
    DEFAULT_FIELDS,
    create_user,
    delete_user,
    list_users,
    update_user,
    validate_fields,
)


def _do_publish(args):
    """Publish a markdown file as a WordPress page."""
    site_url, user, password, admin_path = resolve_config(site_name=args.site)
    title, slug, status, content = parse_page(args.file)

    print(f"Publishing '{title}' as {status} to {site_url}...")
    return publish_page(
        site_url, user, password, title, slug, status, content, admin_path=admin_path
    )


def _do_site_add(args):
    """Create a new site configuration interactively."""
    create_site_config()
    return 0


def _do_site_list(args):
    """List configured sites."""
    sites = list_sites()
    if not sites:
        print("No site configs found. Run 'wpa site add' to create one.")
        return 0
    for name in sites:
        print(name)
    return 0


def _do_user_list(args):
    """List WordPress users."""
    site_url, user, password, _admin_path = resolve_config(site_name=args.site)

    try:
        fields = validate_fields(args.fields)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    rows = list_users(site_url, user, password, role=args.role, search=args.search)

    if not rows:
        print("No users found.")
        return 0

    output = format_output(rows, fields, args.format)
    print(output, end="" if args.format in ("csv", "tsv") else "")
    return 0


def _do_user_create(args):
    """Create a new WordPress user."""
    site_url, user, password, _admin_path = resolve_config(site_name=args.site)

    # Prompt for password if not provided
    new_password = args.password
    if not new_password:
        new_password = getpass.getpass("Password for new user: ")
        if not new_password:
            print("Error: Password cannot be empty.")
            return 1

    result = create_user(
        site_url,
        user,
        password,
        username=args.username,
        email=args.email,
        password_new=new_password,
        role=args.role,
        first_name=args.first_name,
        last_name=args.last_name,
    )
    print("User created successfully!")
    print(f"  ID:       {result['id']}")
    print(f"  Username: {result.get('slug', args.username)}")
    print(f"  Email:    {result.get('email', args.email)}")
    return 0


def _do_user_update(args):
    """Update an existing WordPress user."""
    site_url, user, password, _admin_path = resolve_config(site_name=args.site)

    result = update_user(
        site_url,
        user,
        password,
        user_id=args.id,
        email=args.email,
        role=args.role,
        first_name=args.first_name,
        last_name=args.last_name,
        display_name=args.display_name,
    )
    print(f"User {args.id} updated successfully!")
    print(f"  Display name: {result.get('name', '')}")
    print(f"  Email:        {result.get('email', '')}")
    return 0


def _do_user_delete(args):
    """Delete a WordPress user."""
    site_url, user, password, _admin_path = resolve_config(site_name=args.site)

    if args.reassign is None:
        print(
            "Warning: No --reassign specified. "
            "Posts by this user will be deleted permanently."
        )

    result = delete_user(
        site_url,
        user,
        password,
        user_id=args.id,
        reassign=args.reassign,
    )
    if result.get("deleted"):
        print(f"User {args.id} deleted successfully.")
    else:
        print(f"Unexpected response: {result}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wpa",
        description="WordPress Automation — publish markdown files as WordPress pages.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    # wpa publish <file> [--site NAME]
    publish_parser = subparsers.add_parser(
        "publish",
        help="Publish a markdown file as a WordPress page (shortcut for 'page create')",
    )
    publish_parser.add_argument(
        "file", help="Path to markdown file with YAML frontmatter"
    )
    publish_parser.add_argument(
        "--site", help="Use named site config from ~/.config/wpa/<name>/"
    )
    publish_parser.set_defaults(func=_do_publish)

    # wpa page create <file> [--site NAME]
    page_parser = subparsers.add_parser("page", help="Page management commands")
    page_subparsers = page_parser.add_subparsers(dest="page_command")

    page_create_parser = page_subparsers.add_parser(
        "create", help="Create a WordPress page from a markdown file"
    )
    page_create_parser.add_argument(
        "file", help="Path to markdown file with YAML frontmatter"
    )
    page_create_parser.add_argument(
        "--site", help="Use named site config from ~/.config/wpa/<name>/"
    )
    page_create_parser.set_defaults(func=_do_publish)

    # wpa site add / list
    site_parser = subparsers.add_parser("site", help="Site configuration commands")
    site_subparsers = site_parser.add_subparsers(dest="site_command")

    site_add_parser = site_subparsers.add_parser(
        "add", help="Create a new site config interactively"
    )
    site_add_parser.set_defaults(func=_do_site_add)

    site_list_parser = site_subparsers.add_parser("list", help="List configured sites")
    site_list_parser.set_defaults(func=_do_site_list)

    # wpa user list / create / update / delete
    user_parser = subparsers.add_parser("user", help="User management commands")
    user_subparsers = user_parser.add_subparsers(dest="user_command")

    # wpa user list
    user_list_parser = user_subparsers.add_parser("list", help="List WordPress users")
    user_list_parser.add_argument(
        "--site", help="Use named site config from ~/.config/wpa/<name>/"
    )
    user_list_parser.add_argument(
        "--role", help="Filter by role (e.g., editor, administrator)"
    )
    user_list_parser.add_argument("--search", help="Search by username, email, or name")
    user_list_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json", "csv", "tsv"],
        help="Output format (default: table)",
    )
    user_list_parser.add_argument(
        "--fields",
        default=None,
        help=f"Comma-separated fields to display (default: {','.join(DEFAULT_FIELDS)})",
    )
    user_list_parser.set_defaults(func=_do_user_list)

    # wpa user create
    user_create_parser = user_subparsers.add_parser(
        "create", help="Create a new WordPress user"
    )
    user_create_parser.add_argument(
        "--site", help="Use named site config from ~/.config/wpa/<name>/"
    )
    user_create_parser.add_argument("--username", required=True, help="Login name")
    user_create_parser.add_argument("--email", required=True, help="Email address")
    user_create_parser.add_argument(
        "--password",
        default=None,
        help="Password (prompted interactively if not provided)",
    )
    user_create_parser.add_argument("--role", help="User role (e.g., editor, author)")
    user_create_parser.add_argument("--first-name", help="First name")
    user_create_parser.add_argument("--last-name", help="Last name")
    user_create_parser.set_defaults(func=_do_user_create)

    # wpa user update
    user_update_parser = user_subparsers.add_parser(
        "update", help="Update an existing WordPress user"
    )
    user_update_parser.add_argument("id", type=int, help="User ID to update")
    user_update_parser.add_argument(
        "--site", help="Use named site config from ~/.config/wpa/<name>/"
    )
    user_update_parser.add_argument("--email", help="New email address")
    user_update_parser.add_argument("--role", help="New role")
    user_update_parser.add_argument("--first-name", help="New first name")
    user_update_parser.add_argument("--last-name", help="New last name")
    user_update_parser.add_argument("--display-name", help="New display name")
    user_update_parser.set_defaults(func=_do_user_update)

    # wpa user delete
    user_delete_parser = user_subparsers.add_parser(
        "delete", help="Delete a WordPress user"
    )
    user_delete_parser.add_argument("id", type=int, help="User ID to delete")
    user_delete_parser.add_argument(
        "--site", help="Use named site config from ~/.config/wpa/<name>/"
    )
    user_delete_parser.add_argument(
        "--reassign",
        type=int,
        default=None,
        help="Reassign posts to this user ID (posts deleted if omitted)",
    )
    user_delete_parser.set_defaults(func=_do_user_delete)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "page" and not args.page_command:
        page_parser.print_help()
        return 1

    if args.command == "site" and not args.site_command:
        site_parser.print_help()
        return 1

    if args.command == "user" and not args.user_command:
        user_parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
