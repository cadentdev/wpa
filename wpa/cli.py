"""Command-line interface for WPA — subcommand structure."""

import argparse
import getpass
import json
import sys

from wpa import __version__
from wpa.api import WPApiClient
from wpa.config import create_site_config, list_sites
from wpa.exceptions import WPApiError, WPConnectionError, WPTimeoutError
from wpa.formatter import format_count, format_field, format_ids, format_output
from wpa.post import (
    create_post,
    delete_post,
    get_post,
    list_posts,
    update_post,
    validate_fields as validate_post_fields,
)
from wpa.page import (
    create_page,
    delete_page,
    get_page,
    list_pages,
    update_page,
    validate_fields as validate_page_fields,
)
from wpa.publish import parse_page, publish_page
from wpa.media import (
    delete_media,
    get_media,
    import_media,
    list_media,
    validate_fields as validate_media_fields,
)
from wpa.user import (
    DEFAULT_FIELDS as USER_DEFAULT_FIELDS,
    create_user,
    delete_user,
    get_user,
    list_users,
    set_role,
    update_user,
    validate_fields as validate_user_fields,
)


def _handle_api_error(e):  # pragma: no cover
    """Print an API error and return exit code 1."""
    if isinstance(e, WPApiError):
        print(f"Error: WordPress API returned {e.status_code}")
        print(f"  Code:    {e.code}")
        print(f"  Message: {e.message}")
    elif isinstance(e, WPConnectionError):
        print(f"Error: {e}")
    elif isinstance(e, WPTimeoutError):
        print(f"Error: {e}")
    return 1


def _format_list_output(rows, fields, args):  # pragma: no cover
    """Handle list output with --ids, --count, --field, or standard format."""
    if args.ids:
        result = format_ids(rows)
        if result:
            print(result)
        return 0

    if args.count:
        print(format_count(rows))
        return 0

    if args.field:
        result = format_field(rows, args.field)
        if result:
            print(result)
        return 0

    if not rows:
        print("No results found.")
        return 0

    output = format_output(rows, fields, args.format)
    print(output, end="" if args.format in ("csv", "tsv") else "")
    return 0


# --- Publish handlers ---


def _do_publish(args):  # pragma: no cover
    """Publish a markdown file as a WordPress page."""
    title, slug, status, content = parse_page(args.file)
    client = WPApiClient.from_config(site_name=args.site)

    print(f"Publishing '{title}' as {status} to {client.site_url}...")
    return publish_page(
        client, title, slug, status, content, admin_path=client.admin_path
    )


# --- Site handlers ---


def _do_site_add(args):  # pragma: no cover
    """Create a new site configuration interactively."""
    create_site_config()
    return 0


def _do_site_list(args):  # pragma: no cover
    """List configured sites."""
    sites = list_sites()
    if not sites:
        print("No site configs found. Run 'wpa site add' to create one.")
        return 0
    for name in sites:
        print(name)
    return 0


# --- Post handlers ---


def _do_post_list(args):  # pragma: no cover
    """List WordPress posts."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_post_fields(args.fields)
        rows = list_posts(
            client,
            status=args.status,
            author=args.author,
            search=args.search,
            per_page=args.per_page,
            orderby=args.orderby,
            order=args.order,
            category=args.category,
            tag=args.tag,
        )
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_post_get(args):  # pragma: no cover
    """Get a single WordPress post."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_post(client, args.id, embed=args.embed)

        if args.format == "json":
            print(json.dumps(row, indent=2, ensure_ascii=False))
        else:
            for key, value in row.items():
                print(f"{key}: {value}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_post_create(args):  # pragma: no cover
    """Create a new WordPress post."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)

        # Parse categories and tags from comma-separated strings
        categories = None
        if args.categories:
            categories = [int(c.strip()) for c in args.categories.split(",")]

        tags = None
        if args.tags:
            tags = [int(t.strip()) for t in args.tags.split(",")]

        result = create_post(
            client,
            title=args.title,
            content=args.content or "",
            status=args.status,
            slug=args.slug,
            author=args.author,
            categories=categories,
            tags=tags,
            featured_media=args.featured_media,
        )
        print("Post created successfully!")
        print(f"  ID:     {result['id']}")
        print(f"  Status: {result.get('status', 'draft')}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_post_update(args):  # pragma: no cover
    """Update an existing WordPress post."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)

        fields = {}
        if args.title is not None:
            fields["title"] = args.title
        if args.content is not None:
            fields["content"] = args.content
        if args.status is not None:
            fields["status"] = args.status
        if args.slug is not None:
            fields["slug"] = args.slug

        update_post(client, args.id, **fields)
        print(f"Post {args.id} updated successfully!")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_post_delete(args):  # pragma: no cover
    """Delete a WordPress post."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = delete_post(client, args.id, force=args.force)

        if args.force:
            if result.get("deleted"):
                print(f"Post {args.id} deleted permanently.")
            else:
                print(f"Unexpected response: {result}")
        else:
            print(f"Post {args.id} moved to trash.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


# --- Page handlers ---


def _do_page_list(args):  # pragma: no cover
    """List WordPress pages."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_page_fields(args.fields)
        rows = list_pages(
            client,
            status=args.status,
            search=args.search,
            parent=args.parent,
            per_page=args.per_page,
            orderby=args.orderby,
            order=args.order,
        )
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_page_get(args):  # pragma: no cover
    """Get a single WordPress page."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_page(client, args.id, embed=args.embed)

        if args.format == "json":
            print(json.dumps(row, indent=2, ensure_ascii=False))
        else:
            for key, value in row.items():
                print(f"{key}: {value}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_page_create_dispatch(args):  # pragma: no cover
    """Dispatch page create — markdown file or CLI flags."""
    if args.file:
        return _do_publish(args)
    if not args.title:
        print("Error: Provide a markdown file or --title to create a page.")
        return 1
    return _do_page_create(args)


def _do_page_create(args):  # pragma: no cover
    """Create a new WordPress page from CLI flags."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = create_page(
            client,
            title=args.title,
            content=args.content or "",
            status=args.status,
            slug=args.slug,
            parent=args.parent,
            author=args.author,
            menu_order=args.menu_order,
        )
        print("Page created successfully!")
        print(f"  ID:     {result['id']}")
        print(f"  Status: {result.get('status', 'draft')}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_page_update(args):  # pragma: no cover
    """Update an existing WordPress page."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)

        fields = {}
        if args.title is not None:
            fields["title"] = args.title
        if args.content is not None:
            fields["content"] = args.content
        if args.status is not None:
            fields["status"] = args.status
        if args.slug is not None:
            fields["slug"] = args.slug
        if args.parent is not None:
            fields["parent"] = args.parent

        update_page(client, args.id, **fields)
        print(f"Page {args.id} updated successfully!")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_page_delete(args):  # pragma: no cover
    """Delete a WordPress page."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = delete_page(client, args.id, force=args.force)

        if args.force:
            if result.get("deleted"):
                print(f"Page {args.id} deleted permanently.")
            else:
                print(f"Unexpected response: {result}")
        else:
            print(f"Page {args.id} moved to trash.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


# --- User handlers ---


def _do_user_list(args):  # pragma: no cover
    """List WordPress users."""
    try:
        client = WPApiClient.from_config(site_name=args.site)
        fields = validate_user_fields(args.fields)
        rows = list_users(client, role=args.role, search=args.search)

        if not rows:
            print("No users found.")
            return 0

        output = format_output(rows, fields, args.format)
        print(output, end="" if args.format in ("csv", "tsv") else "")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_user_create(args):  # pragma: no cover
    """Create a new WordPress user."""
    try:
        client = WPApiClient.from_config(site_name=args.site)

        # Prompt for password if not provided
        new_password = args.password
        if not new_password:
            new_password = getpass.getpass("Password for new user: ")
            if not new_password:
                print("Error: Password cannot be empty.")
                return 1

        result = create_user(
            client,
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
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_user_update(args):  # pragma: no cover
    """Update an existing WordPress user."""
    try:
        client = WPApiClient.from_config(site_name=args.site)
        result = update_user(
            client,
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
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_user_delete(args):  # pragma: no cover
    """Delete a WordPress user."""
    try:
        client = WPApiClient.from_config(site_name=args.site)

        if args.reassign is None:
            print(
                "Warning: No --reassign specified. "
                "Posts by this user will be deleted permanently."
            )

        result = delete_user(
            client,
            user_id=args.id,
            reassign=args.reassign,
        )
        if result.get("deleted"):
            print(f"User {args.id} deleted successfully.")
        else:
            print(f"Unexpected response: {result}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_user_get(args):  # pragma: no cover
    """Get a single WordPress user."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_user(client, args.id)
        if args.format == "json":
            print(json.dumps(row, indent=2, ensure_ascii=False))
        else:
            for key, value in row.items():
                print(f"{key}: {value}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_user_set_role(args):  # pragma: no cover
    """Set a WordPress user's role."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = set_role(client, args.id, args.role)
        roles = result.get("roles", [])
        if isinstance(roles, list):
            roles = ", ".join(roles)
        print(f"User {args.id} role set to: {roles}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


# --- Media handlers ---


def _do_media_list(args):  # pragma: no cover
    """List WordPress media."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_media_fields(args.fields)
        rows = list_media(
            client,
            media_type=args.media_type,
            mime_type=args.mime_type,
            search=args.search,
            per_page=args.per_page,
        )
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_media_get(args):  # pragma: no cover
    """Get a single WordPress media item."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_media(client, args.id)
        if args.format == "json":
            print(json.dumps(row, indent=2, ensure_ascii=False))
        else:
            for key, value in row.items():
                print(f"{key}: {value}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_media_import(args):  # pragma: no cover
    """Import a local file as WordPress media."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = import_media(
            client,
            args.file,
            title=args.title,
            alt_text=args.alt_text,
            caption=args.caption,
            description=args.description,
            post=args.post,
        )
        media_id = result.get("id", "unknown")
        source_url = result.get("source_url", "")
        print(f"Media imported successfully. ID: {media_id}")
        if source_url:
            print(f"URL: {source_url}")
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_media_delete(args):  # pragma: no cover
    """Delete a WordPress media item."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = delete_media(client, args.id, force=args.force)
        if result.get("deleted"):
            print(f"Media {args.id} deleted successfully.")
        else:
            print(f"Media {args.id} moved to trash.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


# --- Shared parser factories ---


def _shared_parser():
    """Parent parser with args shared across all resource subcommands."""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--site", help="Use named site config from ~/.config/wpa/<name>/")
    p.add_argument(
        "--debug", action="store_true", help="Print HTTP request/response details"
    )
    return p


def _list_parser():
    """Parent parser for list subcommands with output formatting."""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--format",
        default="table",
        choices=["table", "json", "csv", "tsv"],
        help="Output format (default: table)",
    )
    p.add_argument("--fields", default=None, help="Comma-separated fields to display")
    p.add_argument("--ids", action="store_true", help="Output only resource IDs")
    p.add_argument(
        "--count", action="store_true", help="Output only the count of results"
    )
    p.add_argument(
        "--field",
        default=None,
        metavar="FIELD",
        help="Output a single field per result",
    )
    return p


# --- Main entry point ---


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wpa",
        description="WordPress Automation — manage content and users via the REST API.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")
    shared = _shared_parser()
    list_p = _list_parser()

    # --- wpa publish ---
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

    # --- wpa post ---
    post_parser = subparsers.add_parser("post", help="Post management commands")
    post_subparsers = post_parser.add_subparsers(dest="post_command")

    # wpa post list
    post_list_parser = post_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List posts"
    )
    post_list_parser.add_argument(
        "--status", help="Filter by status (draft, publish, pending, private, trash)"
    )
    post_list_parser.add_argument("--author", type=int, help="Filter by author ID")
    post_list_parser.add_argument("--search", help="Search posts")
    post_list_parser.add_argument(
        "--per-page", type=int, default=10, help="Results per page (default: 10)"
    )
    post_list_parser.add_argument(
        "--orderby",
        help="Sort field (date, title, id, modified, slug)",
    )
    post_list_parser.add_argument("--order", choices=["asc", "desc"], help="Sort order")
    post_list_parser.add_argument("--category", type=int, help="Filter by category ID")
    post_list_parser.add_argument("--tag", type=int, help="Filter by tag ID")
    post_list_parser.set_defaults(func=_do_post_list)

    # wpa post get <id>
    post_get_parser = post_subparsers.add_parser(
        "get", parents=[shared], help="Get a single post"
    )
    post_get_parser.add_argument("id", type=int, help="Post ID")
    post_get_parser.add_argument(
        "--embed", action="store_true", help="Include linked resources"
    )
    post_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    post_get_parser.set_defaults(func=_do_post_get)

    # wpa post create
    post_create_parser = post_subparsers.add_parser(
        "create", parents=[shared], help="Create a new post"
    )
    post_create_parser.add_argument("--title", required=True, help="Post title")
    post_create_parser.add_argument("--content", help="Post content (HTML)")
    post_create_parser.add_argument(
        "--status",
        default="draft",
        help="Post status (default: draft)",
    )
    post_create_parser.add_argument("--slug", help="URL slug")
    post_create_parser.add_argument("--author", type=int, help="Author user ID")
    post_create_parser.add_argument("--categories", help="Comma-separated category IDs")
    post_create_parser.add_argument("--tags", help="Comma-separated tag IDs")
    post_create_parser.add_argument(
        "--featured-media", type=int, help="Featured image media ID"
    )
    post_create_parser.set_defaults(func=_do_post_create)

    # wpa post update <id>
    post_update_parser = post_subparsers.add_parser(
        "update", parents=[shared], help="Update an existing post"
    )
    post_update_parser.add_argument("id", type=int, help="Post ID to update")
    post_update_parser.add_argument("--title", help="New title")
    post_update_parser.add_argument("--content", help="New content (HTML)")
    post_update_parser.add_argument("--status", help="New status")
    post_update_parser.add_argument("--slug", help="New URL slug")
    post_update_parser.set_defaults(func=_do_post_update)

    # wpa post delete <id>
    post_delete_parser = post_subparsers.add_parser(
        "delete", parents=[shared], help="Delete a post"
    )
    post_delete_parser.add_argument("id", type=int, help="Post ID to delete")
    post_delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Permanently delete (skip trash)",
    )
    post_delete_parser.set_defaults(func=_do_post_delete)

    # --- wpa page ---
    page_parser = subparsers.add_parser("page", help="Page management commands")
    page_subparsers = page_parser.add_subparsers(dest="page_command")

    # wpa page list
    page_list_parser = page_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List pages"
    )
    page_list_parser.add_argument(
        "--status", help="Filter by status (draft, publish, pending, private, trash)"
    )
    page_list_parser.add_argument("--search", help="Search pages")
    page_list_parser.add_argument("--parent", type=int, help="Filter by parent page ID")
    page_list_parser.add_argument(
        "--per-page", type=int, default=10, help="Results per page (default: 10)"
    )
    page_list_parser.add_argument(
        "--orderby", help="Sort field (date, title, id, modified, slug, menu_order)"
    )
    page_list_parser.add_argument("--order", choices=["asc", "desc"], help="Sort order")
    page_list_parser.set_defaults(func=_do_page_list)

    # wpa page get <id>
    page_get_parser = page_subparsers.add_parser(
        "get", parents=[shared], help="Get a single page"
    )
    page_get_parser.add_argument("id", type=int, help="Page ID")
    page_get_parser.add_argument(
        "--embed", action="store_true", help="Include linked resources"
    )
    page_get_parser.add_argument(
        "--format", default="table", choices=["table", "json"], help="Output format"
    )
    page_get_parser.set_defaults(func=_do_page_get)

    # wpa page create (from flags or markdown file)
    page_create_parser = page_subparsers.add_parser(
        "create", parents=[shared], help="Create a new page"
    )
    page_create_parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Path to markdown file with YAML frontmatter",
    )
    page_create_parser.add_argument("--title", help="Page title")
    page_create_parser.add_argument("--content", help="Page content (HTML)")
    page_create_parser.add_argument(
        "--status", default="draft", help="Page status (default: draft)"
    )
    page_create_parser.add_argument("--slug", help="URL slug")
    page_create_parser.add_argument("--parent", type=int, help="Parent page ID")
    page_create_parser.add_argument("--author", type=int, help="Author user ID")
    page_create_parser.add_argument("--menu-order", type=int, help="Menu order")
    page_create_parser.set_defaults(func=_do_page_create_dispatch)

    # wpa page update <id>
    page_update_parser = page_subparsers.add_parser(
        "update", parents=[shared], help="Update an existing page"
    )
    page_update_parser.add_argument("id", type=int, help="Page ID to update")
    page_update_parser.add_argument("--title", help="New title")
    page_update_parser.add_argument("--content", help="New content (HTML)")
    page_update_parser.add_argument("--status", help="New status")
    page_update_parser.add_argument("--slug", help="New URL slug")
    page_update_parser.add_argument("--parent", type=int, help="New parent page ID")
    page_update_parser.set_defaults(func=_do_page_update)

    # wpa page delete <id>
    page_delete_parser = page_subparsers.add_parser(
        "delete", parents=[shared], help="Delete a page"
    )
    page_delete_parser.add_argument("id", type=int, help="Page ID to delete")
    page_delete_parser.add_argument(
        "--force", action="store_true", help="Permanently delete (skip trash)"
    )
    page_delete_parser.set_defaults(func=_do_page_delete)

    # --- wpa site ---
    site_parser = subparsers.add_parser("site", help="Site configuration commands")
    site_subparsers = site_parser.add_subparsers(dest="site_command")

    site_add_parser = site_subparsers.add_parser(
        "add", help="Create a new site config interactively"
    )
    site_add_parser.set_defaults(func=_do_site_add)

    site_list_parser = site_subparsers.add_parser("list", help="List configured sites")
    site_list_parser.set_defaults(func=_do_site_list)

    # --- wpa user ---
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
        help=f"Comma-separated fields to display (default: {','.join(USER_DEFAULT_FIELDS)})",
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

    # wpa user get <id>
    user_get_parser = user_subparsers.add_parser(
        "get", parents=[shared], help="Get a single user"
    )
    user_get_parser.add_argument("id", type=int, help="User ID")
    user_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    user_get_parser.set_defaults(func=_do_user_get)

    # wpa user set-role <id> <role>
    user_set_role_parser = user_subparsers.add_parser(
        "set-role", parents=[shared], help="Set a user's role"
    )
    user_set_role_parser.add_argument("id", type=int, help="User ID")
    user_set_role_parser.add_argument(
        "role",
        help="Role name (administrator, editor, author, contributor, subscriber)",
    )
    user_set_role_parser.set_defaults(func=_do_user_set_role)

    # --- wpa media ---
    media_parser = subparsers.add_parser("media", help="Media management commands")
    media_subparsers = media_parser.add_subparsers(dest="media_command")

    # wpa media list
    media_list_parser = media_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List media"
    )
    media_list_parser.add_argument(
        "--media-type",
        help="Filter by media type (image, video, audio, application)",
    )
    media_list_parser.add_argument(
        "--mime-type", help="Filter by MIME type (e.g., image/jpeg)"
    )
    media_list_parser.add_argument("--search", help="Search media")
    media_list_parser.add_argument(
        "--per-page",
        type=int,
        default=10,
        help="Results per page (default: 10)",
    )
    media_list_parser.set_defaults(func=_do_media_list)

    # wpa media get <id>
    media_get_parser = media_subparsers.add_parser(
        "get", parents=[shared], help="Get a single media item"
    )
    media_get_parser.add_argument("id", type=int, help="Media ID")
    media_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    media_get_parser.set_defaults(func=_do_media_get)

    # wpa media import <file>
    media_import_parser = media_subparsers.add_parser(
        "import", parents=[shared], help="Upload a local file as media"
    )
    media_import_parser.add_argument("file", help="Path to the file to upload")
    media_import_parser.add_argument("--title", help="Media title")
    media_import_parser.add_argument("--alt-text", help="Alt text for images")
    media_import_parser.add_argument("--caption", help="Media caption")
    media_import_parser.add_argument("--description", help="Media description")
    media_import_parser.add_argument("--post", type=int, help="Parent post ID")
    media_import_parser.set_defaults(func=_do_media_import)

    # wpa media delete <id>
    media_delete_parser = media_subparsers.add_parser(
        "delete", parents=[shared], help="Delete a media item"
    )
    media_delete_parser.add_argument("id", type=int, help="Media ID to delete")
    media_delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Permanently delete (skip trash)",
    )
    media_delete_parser.set_defaults(func=_do_media_delete)

    # --- Parse and dispatch ---
    args = parser.parse_args(argv)

    if not args.command:  # pragma: no cover
        parser.print_help()
        return 1

    if args.command == "post" and not args.post_command:  # pragma: no cover
        post_parser.print_help()
        return 1

    if args.command == "page" and not args.page_command:  # pragma: no cover
        page_parser.print_help()
        return 1

    if args.command == "site" and not args.site_command:  # pragma: no cover
        site_parser.print_help()
        return 1

    if args.command == "user" and not args.user_command:  # pragma: no cover
        user_parser.print_help()
        return 1

    if args.command == "media" and not args.media_command:  # pragma: no cover
        media_parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
