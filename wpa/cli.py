"""Command-line interface for WPA — subcommand structure."""

import argparse
import sys

from wpa import __version__
from wpa.config import create_site_config, list_sites, resolve_config
from wpa.publish import parse_page, publish_page


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

    # wpa site add
    # wpa site list
    site_parser = subparsers.add_parser("site", help="Site configuration commands")
    site_subparsers = site_parser.add_subparsers(dest="site_command")

    site_add_parser = site_subparsers.add_parser(
        "add", help="Create a new site config interactively"
    )
    site_add_parser.set_defaults(func=_do_site_add)

    site_list_parser = site_subparsers.add_parser("list", help="List configured sites")
    site_list_parser.set_defaults(func=_do_site_list)

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

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
