"""Command-line interface for WPA — subcommand structure."""

import argparse
import json
import sys

from wpa import __version__
from wpa.api import WPApiClient
from wpa.block import (
    get_block,
    list_blocks,
)
from wpa.block import (
    validate_fields as validate_block_fields,
)
from wpa.comment import (
    COUNT_STATUSES as COMMENT_COUNT_STATUSES,
)
from wpa.comment import (
    approve_comment,
    count_comments,
    create_comment,
    delete_comment,
    get_comment,
    list_comments,
    spam_comment,
    trash_comment,
    unapprove_comment,
    unspam_comment,
    update_comment,
)
from wpa.comment import (
    validate_fields as validate_comment_fields,
)
from wpa.config import create_site_config, list_sites
from wpa.exceptions import WPApiError, WPConnectionError, WPTimeoutError
from wpa.formatter import format_count, format_field, format_ids, format_output
from wpa.media import (
    delete_media,
    get_media,
    import_media,
    list_media,
)
from wpa.media import (
    validate_fields as validate_media_fields,
)
from wpa.menu import (
    LOCATION_DEFAULT_FIELDS as MENU_LOCATION_FIELDS,
)
from wpa.menu import (
    create_menu,
    create_menu_item,
    delete_menu,
    delete_menu_item,
    get_menu,
    list_menu_items,
    list_menu_locations,
    list_menus,
    update_menu_item,
    validate_item_fields,
    validate_menu_fields,
)
from wpa.option import (
    get_setting,
    list_settings,
    update_setting,
)
from wpa.option import (
    validate_fields as validate_option_fields,
)
from wpa.page import (
    create_page,
    delete_page,
    get_page,
    list_pages,
    update_page,
)
from wpa.page import (
    validate_fields as validate_page_fields,
)
from wpa.plugin import (
    activate_plugin,
    deactivate_plugin,
    get_plugin,
    list_plugins,
)
from wpa.plugin import (
    validate_fields as validate_plugin_fields,
)
from wpa.post import (
    create_post,
    delete_post,
    get_post,
    list_posts,
    update_post,
)
from wpa.post import (
    validate_fields as validate_post_fields,
)
from wpa.post_type import (
    get_post_type,
    list_post_types,
)
from wpa.post_type import (
    validate_fields as validate_post_type_fields,
)
from wpa.publish import parse_markdown, publish_page, resolve_file_fields
from wpa.sidebar import (
    list_sidebars,
)
from wpa.sidebar import (
    validate_fields as validate_sidebar_fields,
)
from wpa.taxonomy import (
    get_taxonomy,
    list_taxonomies,
)
from wpa.taxonomy import (
    validate_fields as validate_taxonomy_fields,
)
from wpa.term import (
    create_term,
    delete_term,
    get_term,
    list_terms,
    update_term,
)
from wpa.term import (
    validate_fields as validate_term_fields,
)
from wpa.theme import (
    THEME_STATUSES,
    get_theme,
    list_themes,
)
from wpa.theme import (
    validate_fields as validate_theme_fields,
)
from wpa.user import (
    DEFAULT_FIELDS as USER_DEFAULT_FIELDS,
)
from wpa.user import (
    create_user,
    delete_user,
    generate_password,
    get_user,
    list_users,
    set_role,
    update_user,
)
from wpa.user import (
    validate_fields as validate_user_fields,
)
from wpa.widget import (
    deactivate_widget,
    delete_widget,
    get_widget,
    list_widgets,
    update_widget,
)
from wpa.widget import (
    validate_fields as validate_widget_fields,
)


def _format_api_error(e):
    """Build the user-facing message for an API exception.

    Known machine codes get a multi-line explanation of what happened and
    what to check; everything else falls back to the generic status/code/
    message block.
    """
    if not isinstance(e, WPApiError):
        return f"Error: {e}"

    if e.code == "tls_downgrade":
        return (
            "Error: the connection was downgraded from https to http.\n"
            "  WPA refused the response because your credentials would travel\n"
            "  unencrypted. This is usually a misconfigured redirect on the\n"
            "  server, load balancer, or CDN — or a man-in-the-middle.\n"
            "  Check that WP_SITE_URL is the site's canonical https address\n"
            "  (right host, with/without 'www') and that the server does not\n"
            "  redirect API requests to http.\n"
            "  See GETTING-STARTED.md, 'TLS troubleshooting'."
        )

    if e.code == "possible_waf_block":
        return (
            f"Error: the server returned an HTML page (HTTP {e.status_code}) "
            "instead of a REST API JSON response.\n"
            "  This usually means a security plugin or WAF (e.g. Wordfence)\n"
            "  blocked the request before it reached WordPress. Known triggers:\n"
            "  DELETE requests and the ?author= query parameter.\n"
            "  See docs/waf-compatibility.md for symptoms and fixes."
        )

    return (
        f"Error: WordPress API returned {e.status_code}\n"
        f"  Code:    {e.code}\n"
        f"  Message: {e.message}"
    )


def _handle_api_error(e):  # pragma: no cover
    """Print an API error and return exit code 1."""
    print(_format_api_error(e))
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
    print(output, end="")
    return 0


# --- Publish handlers ---


def _do_publish(args):  # pragma: no cover
    """Publish a markdown file as a WordPress page."""
    try:
        data = parse_markdown(args.file)
        # Frontmatter supplies author too; --author wins when both are given.
        title, content, status, slug, author = resolve_file_fields(
            data, author=args.author
        )
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    client = WPApiClient.from_config(site_name=args.site)

    print(f"Publishing '{title}' as {status} to {client.site_url}...")
    return publish_page(
        client,
        title,
        slug,
        status,
        content,
        admin_path=client.admin_path,
        author=author,
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
        if args.file and args.content:
            print("Error: --file and --content are mutually exclusive.")
            return 1
        if not args.file and not args.title:
            print("Error: Provide --title, or --file with a markdown file.")
            return 1

        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)

        # Parse categories and tags from comma-separated strings
        categories = None
        if args.categories:
            categories = [int(c.strip()) for c in args.categories.split(",")]

        tags = None
        if args.tags:
            tags = [int(t.strip()) for t in args.tags.split(",")]

        if args.file:
            # Markdown file: frontmatter supplies title/status/slug/author and
            # the body converts to HTML; explicit CLI flags win over frontmatter.
            data = parse_markdown(args.file)
            title, content, status, slug, author = resolve_file_fields(
                data,
                title=args.title,
                status=args.status,
                slug=args.slug,
                author=args.author,
            )
        else:
            title = args.title
            content = args.content or ""
            status = args.status or "draft"
            slug = args.slug
            author = args.author

        result = create_post(
            client,
            title=title,
            content=content,
            status=status,
            slug=slug,
            author=author,
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
    """Dispatch page create — markdown file (positional or --file) or flags."""
    if args.file and args.file_opt:
        print("Error: pass the markdown file once (positional or --file).")
        return 1
    file_path = args.file or args.file_opt
    if file_path and args.content:
        print("Error: --file and --content are mutually exclusive.")
        return 1
    if not file_path and not args.title:
        print("Error: Provide a markdown file or --title to create a page.")
        return 1
    return _do_page_create(args, file_path=file_path)


def _do_page_create(args, file_path=None):  # pragma: no cover
    """Create a new WordPress page from a markdown file and/or CLI flags."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)

        if file_path:
            # Frontmatter supplies title/status/slug/author and the body
            # converts to HTML; explicit CLI flags win over frontmatter.
            data = parse_markdown(file_path)
            title, content, status, slug, author = resolve_file_fields(
                data,
                title=args.title,
                status=args.status,
                slug=args.slug,
                author=args.author,
            )
        else:
            title = args.title
            content = args.content or ""
            status = args.status or "draft"
            slug = args.slug
            author = args.author

        result = create_page(
            client,
            title=title,
            content=content,
            status=status,
            slug=slug,
            parent=args.parent,
            author=author,
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
        print(output, end="")
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

        # Password acquisition: --password-stdin, else a generated strong
        # random password that is never displayed or stored. The operator
        # handling a credential is the anti-pattern here — the blessed flow
        # is a generated password plus --send-email, so the new user sets
        # their own password via a one-time link (mirroring wp-admin).
        generated = False
        if getattr(args, "password_stdin", False):
            new_password = sys.stdin.readline().rstrip("\n")
            if not new_password:
                print("Error: Password cannot be empty.")
                return 1
        else:
            new_password = generate_password()
            generated = True

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
        if generated:
            print("  Password: (generated — not displayed)")

        if getattr(args, "send_email", False):
            sent = client.request_password_reset(args.username)
            if sent:
                print(
                    f"Set-password email requested for '{args.username}'. "
                    "WordPress accepted the request (the subject line reads "
                    "'Password Reset'). A send is not a delivery — confirm "
                    "with the recipient or the site's mail log."
                )
                return 0
            print(
                "Warning: WordPress did NOT confirm the set-password email "
                f"for '{args.username}'. A security plugin may be blocking "
                "or rate-limiting wp-login.php?action=lostpassword. The "
                f"account exists (ID {result['id']}) but nobody has been "
                "notified. Send the user a set-password link via the site's "
                "'Lost your password?' page.",
                file=sys.stderr,
            )
            return 1

        print(
            "Note: no notification email was sent — the WordPress REST API "
            "cannot send one. The new user has not been told this account "
            "exists. Use --send-email to send a one-time set-password link, "
            "or point the user at the site's 'Lost your password?' page.",
            file=sys.stderr,
        )
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


# --- Comment handlers ---


def _do_block_list(args):  # pragma: no cover
    """List registered block types."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_block_fields(args.fields)
        rows = list_blocks(client, namespace=args.namespace)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_block_get(args):  # pragma: no cover
    """Get a single registered block type."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_block(client, args.block)
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


def _do_theme_list(args):  # pragma: no cover
    """List installed themes."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_theme_fields(args.fields)
        status = None if args.status == "all" else args.status
        rows = list_themes(client, status=status)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_theme_get(args):  # pragma: no cover
    """Get a single installed theme."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_theme(client, args.stylesheet)
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


def _do_taxonomy_list(args):  # pragma: no cover
    """List registered taxonomies."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_taxonomy_fields(args.fields)
        rows = list_taxonomies(client)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_taxonomy_get(args):  # pragma: no cover
    """Get a single registered taxonomy."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_taxonomy(client, args.taxonomy)
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


def _do_post_type_list(args):  # pragma: no cover
    """List registered post types."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_post_type_fields(args.fields)
        rows = list_post_types(client)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_post_type_get(args):  # pragma: no cover
    """Get a single registered post type."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_post_type(client, args.post_type)
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


def _do_plugin_list(args):  # pragma: no cover
    """List installed WordPress plugins."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_plugin_fields(args.fields)
        rows = list_plugins(client, status=args.status, search=args.search)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_plugin_get(args):  # pragma: no cover
    """Get a single installed plugin."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_plugin(client, args.plugin)
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


def _do_plugin_toggle(action_func, action_label):  # pragma: no cover
    """Build an activate/deactivate handler that prints the new status."""

    def handler(args):
        try:
            client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
            result = action_func(client, args.plugin)
            print(
                f"Plugin {result.get('plugin', args.plugin)} {action_label} "
                f"(status: {result.get('status', '')})."
            )
            return 0
        except ValueError as e:
            print(f"Error: {e}")
            return 1
        except (WPApiError, WPConnectionError, WPTimeoutError) as e:
            return _handle_api_error(e)

    return handler


def _do_plugin_activate(args):  # pragma: no cover
    return _do_plugin_toggle(activate_plugin, "activated")(args)


def _do_plugin_deactivate(args):  # pragma: no cover
    return _do_plugin_toggle(deactivate_plugin, "deactivated")(args)


def _do_menu_list(args):  # pragma: no cover
    """List nav menus."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_menu_fields(args.fields)
        rows = list_menus(client, search=args.search)
        if not rows and not (args.ids or args.count or args.field):
            print(
                "No menus found. Block themes have no classic nav menus; "
                "this is expected on a block theme."
            )
            return 0
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_get(args):  # pragma: no cover
    """Get a single nav menu."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_menu(client, args.id)
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


def _do_menu_create(args):  # pragma: no cover
    """Create a nav menu."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = create_menu(client, args.name, description=args.description)
        print("Menu created successfully!")
        print(f"  ID:   {result.get('id')}")
        print(f"  Name: {result.get('name')}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_delete(args):  # pragma: no cover
    """Delete a nav menu (always permanent; its items go with it)."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        delete_menu(client, args.id)
        print(f"Menu {args.id} deleted permanently (menus cannot be trashed).")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_item_list(args):  # pragma: no cover
    """List menu items."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_item_fields(args.fields)
        rows = list_menu_items(client, menu=args.menu)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_item_add(args):  # pragma: no cover
    """Add an item to a nav menu."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = create_menu_item(
            client,
            args.menu,
            title=args.title,
            url=args.url,
            object_type=args.object,
            object_id=args.object_id,
            item_type=args.type,
            parent=args.parent,
            position=args.position,
        )
        print("Menu item added successfully!")
        print(f"  ID:   {result.get('id')}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_item_update(args):  # pragma: no cover
    """Update a menu item."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = {}
        if args.title is not None:
            fields["title"] = args.title
        if args.url is not None:
            fields["url"] = args.url
        if args.parent is not None:
            fields["parent"] = args.parent
        if args.position is not None:
            fields["menu_order"] = args.position
        update_menu_item(client, args.id, **fields)
        print(f"Menu item {args.id} updated successfully!")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_item_delete(args):  # pragma: no cover
    """Delete a menu item (always permanent)."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        delete_menu_item(client, args.id)
        print(f"Menu item {args.id} deleted permanently.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_menu_location_list(args):  # pragma: no cover
    """List registered menu locations."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        rows = list_menu_locations(client)
        return _format_list_output(rows, MENU_LOCATION_FIELDS, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_option_list(args):  # pragma: no cover
    """List registered site settings."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_option_fields(args.fields)
        rows = list_settings(client)
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_option_get(args):  # pragma: no cover
    """Get a single registered setting's value."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        value = get_setting(client, args.name)
        if args.format == "json":
            print(json.dumps(value, indent=2, ensure_ascii=False))
        else:
            print(value)
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_option_update(args):  # pragma: no cover
    """Update a single registered setting."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        new_value = update_setting(client, args.name, args.value)
        print(f"Setting '{args.name}' updated.")
        print(f"  New value: {new_value!r}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_sidebar_list(args):  # pragma: no cover
    """List registered sidebars."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_sidebar_fields(args.fields)
        rows = list_sidebars(client)
        if not rows and not (args.ids or args.count or args.field):
            print(
                "No sidebars found. Block themes register no classic "
                "sidebars; this is expected on a block theme."
            )
            return 0
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_widget_list(args):  # pragma: no cover
    """List classic widgets."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_widget_fields(args.fields)
        rows = list_widgets(client, sidebar=args.sidebar)
        if not rows and not (args.ids or args.count or args.field):
            print(
                "No widgets found. Block themes manage widgets as blocks; "
                "this is expected on a block theme."
            )
            return 0
        return _format_list_output(rows, fields, args)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_widget_get(args):  # pragma: no cover
    """Get a single widget."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_widget(client, args.id)
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


def _do_widget_update(args):  # pragma: no cover
    """Move a widget and/or update its instance settings."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        update_widget(
            client, args.id, sidebar=args.sidebar, instance_json=args.instance_json
        )
        print(f"Widget {args.id} updated successfully!")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_widget_deactivate(args):  # pragma: no cover
    """Move a widget to the inactive sidebar."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        deactivate_widget(client, args.id)
        print(f"Widget {args.id} moved to the inactive sidebar (settings kept).")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_widget_delete(args):  # pragma: no cover
    """Delete a widget (inactive-sidebar by default, --force removes)."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        delete_widget(client, args.id, force=args.force)
        if args.force:
            print(f"Widget {args.id} removed entirely.")
        else:
            print(
                f"Widget {args.id} moved to the inactive sidebar "
                "(use --force to remove entirely)."
            )
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_comment_list(args):  # pragma: no cover
    """List WordPress comments."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_comment_fields(args.fields)
        rows = list_comments(
            client,
            post=args.post,
            status=args.status,
            parent=args.parent,
            author_email=args.author_email,
            search=args.search,
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


def _do_comment_get(args):  # pragma: no cover
    """Get a single WordPress comment."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_comment(client, args.id)
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


def _do_comment_create(args):  # pragma: no cover
    """Create a new WordPress comment."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = create_comment(
            client,
            post=args.post,
            content=args.content,
            author_name=args.author_name,
            author_email=args.author_email,
            parent=args.parent,
            status=args.status,
        )
        print("Comment created successfully!")
        print(f"  ID:     {result.get('id')}")
        print(f"  Status: {result.get('status', '')}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_comment_update(args):  # pragma: no cover
    """Update an existing WordPress comment."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = {}
        if args.content is not None:
            fields["content"] = args.content
        if args.status is not None:
            fields["status"] = args.status
        if args.author_name is not None:
            fields["author_name"] = args.author_name
        if args.author_email is not None:
            fields["author_email"] = args.author_email
        update_comment(client, args.id, **fields)
        print(f"Comment {args.id} updated successfully!")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_comment_delete(args):  # pragma: no cover
    """Delete a WordPress comment."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = delete_comment(client, args.id, force=args.force)
        if args.force:
            if result.get("deleted"):
                print(f"Comment {args.id} deleted permanently.")
            else:
                print(f"Unexpected response: {result}")
        else:
            print(f"Comment {args.id} moved to trash.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_comment_moderation(action_func, action_label):  # pragma: no cover
    """Build a moderation handler that calls action_func and prints status."""

    def handler(args):
        try:
            client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
            result = action_func(client, args.id)
            status = result.get("status", "")
            print(f"Comment {args.id} {action_label} (status: {status}).")
            return 0
        except ValueError as e:
            print(f"Error: {e}")
            return 1
        except (WPApiError, WPConnectionError, WPTimeoutError) as e:
            return _handle_api_error(e)

    return handler


def _do_comment_approve(args):  # pragma: no cover
    return _do_comment_moderation(approve_comment, "approved")(args)


def _do_comment_unapprove(args):  # pragma: no cover
    return _do_comment_moderation(unapprove_comment, "unapproved")(args)


def _do_comment_spam(args):  # pragma: no cover
    return _do_comment_moderation(spam_comment, "marked as spam")(args)


def _do_comment_unspam(args):  # pragma: no cover
    return _do_comment_moderation(unspam_comment, "restored from spam")(args)


def _do_comment_trash(args):  # pragma: no cover
    """Move a comment to trash (DELETE without force)."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        trash_comment(client, args.id)
        print(f"Comment {args.id} moved to trash.")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_comment_count(args):  # pragma: no cover
    """Count comments per moderation status."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        counts = count_comments(client, status=args.status)

        if args.status:
            print(counts[args.status])
            return 0

        if args.format == "json":
            print(json.dumps(counts))
            return 0

        width = max(len(s) for s in counts) + 1
        for s, n in counts.items():
            print(f"{s + ':':<{width}} {n}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


# --- Term handlers ---


def _do_term_list(args):  # pragma: no cover
    """List WordPress terms in a taxonomy."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = validate_term_fields(args.fields)
        rows = list_terms(
            client,
            taxonomy=args.taxonomy,
            search=args.search,
            parent=args.parent,
            hide_empty=args.hide_empty,
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


def _do_term_get(args):  # pragma: no cover
    """Get a single WordPress term."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        row = get_term(client, args.id, taxonomy=args.taxonomy)
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


def _do_term_create(args):  # pragma: no cover
    """Create a new WordPress term."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = create_term(
            client,
            name=args.name,
            taxonomy=args.taxonomy,
            slug=args.slug,
            description=args.description,
            parent=args.parent,
        )
        print("Term created successfully!")
        print(f"  ID:   {result.get('id')}")
        print(f"  Name: {result.get('name', args.name)}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_term_update(args):  # pragma: no cover
    """Update an existing WordPress term."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        fields = {}
        if args.name is not None:
            fields["name"] = args.name
        if args.slug is not None:
            fields["slug"] = args.slug
        if args.description is not None:
            fields["description"] = args.description
        if args.parent is not None:
            fields["parent"] = args.parent
        update_term(client, args.id, taxonomy=args.taxonomy, **fields)
        print(f"Term {args.id} updated successfully!")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except (WPApiError, WPConnectionError, WPTimeoutError) as e:
        return _handle_api_error(e)


def _do_term_delete(args):  # pragma: no cover
    """Delete a WordPress term (always force-deleted; terms cannot be trashed)."""
    try:
        client = WPApiClient.from_config(site_name=args.site, debug=args.debug)
        result = delete_term(client, args.id, taxonomy=args.taxonomy)
        if result.get("deleted"):
            print(f"Term {args.id} deleted.")
        else:
            print(f"Unexpected response: {result}")
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
    publish_parser.add_argument(
        "--author",
        type=int,
        help="Author user ID (overrides frontmatter 'author')",
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
    post_create_parser.add_argument(
        "--title", help="Post title (required unless --file supplies one)"
    )
    post_create_parser.add_argument("--content", help="Post content (HTML)")
    post_create_parser.add_argument(
        "--file",
        help=(
            "Markdown file with YAML frontmatter; the body is converted to "
            "HTML. CLI flags override frontmatter. Mutually exclusive with "
            "--content."
        ),
    )
    post_create_parser.add_argument(
        "--status",
        default=None,
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
    page_create_parser.add_argument(
        "--file",
        dest="file_opt",
        help=(
            "Markdown file with YAML frontmatter (same as the positional "
            "argument). CLI flags override frontmatter. Mutually exclusive "
            "with --content."
        ),
    )
    page_create_parser.add_argument("--title", help="Page title")
    page_create_parser.add_argument("--content", help="Page content (HTML)")
    page_create_parser.add_argument(
        "--status", default=None, help="Page status (default: draft)"
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
        "--password-stdin",
        action="store_true",
        help=(
            "Read the password from stdin. If omitted, a strong random "
            "password is generated and never displayed — pair with "
            "--send-email so the user sets their own."
        ),
    )
    user_create_parser.add_argument(
        "--send-email",
        action="store_true",
        help=(
            "After creating the user, trigger WordPress core's lost-password "
            "flow to email them a one-time set-password link. Without this "
            "flag no email is sent — the REST API cannot send one."
        ),
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

    # --- wpa taxonomy ---
    taxonomy_parser = subparsers.add_parser(
        "taxonomy",
        help="Inspect registered taxonomies (read-only)",
    )
    taxonomy_subparsers = taxonomy_parser.add_subparsers(dest="taxonomy_command")

    # wpa taxonomy list
    taxonomy_list_parser = taxonomy_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List registered taxonomies"
    )
    taxonomy_list_parser.set_defaults(func=_do_taxonomy_list)

    # wpa taxonomy get <slug>
    taxonomy_get_parser = taxonomy_subparsers.add_parser(
        "get", parents=[shared], help="Get a single registered taxonomy"
    )
    taxonomy_get_parser.add_argument("taxonomy", help="Taxonomy slug (e.g. category)")
    taxonomy_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    taxonomy_get_parser.set_defaults(func=_do_taxonomy_get)

    # --- wpa post-type ---
    post_type_parser = subparsers.add_parser(
        "post-type",
        help="Inspect registered post types (read-only)",
    )
    post_type_subparsers = post_type_parser.add_subparsers(dest="post_type_command")

    # wpa post-type list
    post_type_list_parser = post_type_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List registered post types"
    )
    post_type_list_parser.set_defaults(func=_do_post_type_list)

    # wpa post-type get <slug>
    post_type_get_parser = post_type_subparsers.add_parser(
        "get", parents=[shared], help="Get a single registered post type"
    )
    post_type_get_parser.add_argument("post_type", help="Post type slug (e.g. post)")
    post_type_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    post_type_get_parser.set_defaults(func=_do_post_type_get)

    # --- wpa block ---
    block_parser = subparsers.add_parser(
        "block",
        help="Inspect registered block types (read-only)",
    )
    block_subparsers = block_parser.add_subparsers(dest="block_command")

    # wpa block list
    block_list_parser = block_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List registered block types"
    )
    block_list_parser.add_argument(
        "--namespace", help="Filter by block namespace (e.g. core)"
    )
    block_list_parser.set_defaults(func=_do_block_list)

    # wpa block get <name>
    block_get_parser = block_subparsers.add_parser(
        "get", parents=[shared], help="Get a single registered block type"
    )
    block_get_parser.add_argument(
        "block", help="Namespaced block name (e.g. core/paragraph)"
    )
    block_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    block_get_parser.set_defaults(func=_do_block_get)

    # --- wpa theme ---
    theme_parser = subparsers.add_parser(
        "theme",
        help="Read-only theme information (listing all requires switch_themes)",
    )
    theme_subparsers = theme_parser.add_subparsers(dest="theme_command")

    # wpa theme list
    theme_list_parser = theme_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List installed themes"
    )
    theme_list_parser.add_argument(
        "--status",
        choices=[*THEME_STATUSES, "all"],
        default="all",
        help="Filter by status (default: all)",
    )
    theme_list_parser.set_defaults(func=_do_theme_list)

    # wpa theme get <stylesheet>
    theme_get_parser = theme_subparsers.add_parser(
        "get", parents=[shared], help="Get a single installed theme"
    )
    theme_get_parser.add_argument(
        "stylesheet", help="Theme stylesheet (e.g. twentytwentyfive)"
    )
    theme_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    theme_get_parser.set_defaults(func=_do_theme_get)

    # --- wpa plugin ---
    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Plugin management commands (requires activate_plugins capability)",
    )
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command")

    # wpa plugin list
    plugin_list_parser = plugin_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List installed plugins"
    )
    plugin_list_parser.add_argument(
        "--status",
        choices=["active", "inactive", "all"],
        default="all",
        help="Filter by activation status (default: all)",
    )
    plugin_list_parser.add_argument("--search", help="Search installed plugins")
    plugin_list_parser.set_defaults(func=_do_plugin_list)

    # wpa plugin get <plugin>
    plugin_get_parser = plugin_subparsers.add_parser(
        "get", parents=[shared], help="Get a single installed plugin"
    )
    plugin_get_parser.add_argument(
        "plugin", help="Plugin identifier (e.g. akismet/akismet)"
    )
    plugin_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    plugin_get_parser.set_defaults(func=_do_plugin_get)

    # wpa plugin activate/deactivate <plugin>
    for action_name, action_func, help_text in (
        ("activate", _do_plugin_activate, "Activate an installed plugin"),
        ("deactivate", _do_plugin_deactivate, "Deactivate an installed plugin"),
    ):
        action_parser = plugin_subparsers.add_parser(
            action_name, parents=[shared], help=help_text
        )
        action_parser.add_argument(
            "plugin", help="Plugin identifier (e.g. akismet/akismet)"
        )
        action_parser.set_defaults(func=action_func)

    # --- wpa menu ---
    menu_parser = subparsers.add_parser(
        "menu",
        help="Nav menu commands (requires edit_theme_options capability)",
    )
    menu_subparsers = menu_parser.add_subparsers(dest="menu_command")

    # wpa menu list
    menu_list_parser = menu_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List nav menus"
    )
    menu_list_parser.add_argument("--search", help="Search menus")
    menu_list_parser.set_defaults(func=_do_menu_list)

    # wpa menu get <id>
    menu_get_parser = menu_subparsers.add_parser(
        "get", parents=[shared], help="Get a single nav menu"
    )
    menu_get_parser.add_argument("id", type=int, help="Menu ID")
    menu_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    menu_get_parser.set_defaults(func=_do_menu_get)

    # wpa menu create
    menu_create_parser = menu_subparsers.add_parser(
        "create", parents=[shared], help="Create a nav menu"
    )
    menu_create_parser.add_argument("--name", required=True, help="Menu name")
    menu_create_parser.add_argument("--description", help="Menu description")
    menu_create_parser.set_defaults(func=_do_menu_create)

    # wpa menu delete <id>
    menu_delete_parser = menu_subparsers.add_parser(
        "delete",
        parents=[shared],
        help="Delete a nav menu (always permanent; deletes its items too)",
    )
    menu_delete_parser.add_argument("id", type=int, help="Menu ID to delete")
    menu_delete_parser.set_defaults(func=_do_menu_delete)

    # wpa menu item <subcommand>
    menu_item_parser = menu_subparsers.add_parser("item", help="Menu item commands")
    menu_item_subparsers = menu_item_parser.add_subparsers(dest="menu_item_command")

    # wpa menu item list --menu <id>
    item_list_parser = menu_item_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List menu items"
    )
    item_list_parser.add_argument("--menu", type=int, help="Filter to one menu's items")
    item_list_parser.set_defaults(func=_do_menu_item_list)

    # wpa menu item add <menu-id>
    item_add_parser = menu_item_subparsers.add_parser(
        "add", parents=[shared], help="Add an item to a menu"
    )
    item_add_parser.add_argument("menu", type=int, help="Menu ID to add to")
    item_add_parser.add_argument(
        "--title", help="Link text (required for custom links)"
    )
    item_add_parser.add_argument("--url", help="Target URL (custom link items)")
    item_add_parser.add_argument(
        "--object",
        help="Linked object slug (page, post, category, post_tag, ...)",
    )
    item_add_parser.add_argument(
        "--object-id", type=int, help="ID of the linked object"
    )
    item_add_parser.add_argument(
        "--type",
        help="Explicit item type (custom, post_type, taxonomy); "
        "inferred from --url/--object when omitted",
    )
    item_add_parser.add_argument(
        "--parent", type=int, help="Parent item ID for nested menus"
    )
    item_add_parser.add_argument("--position", type=int, help="Menu order (1-based)")
    item_add_parser.set_defaults(func=_do_menu_item_add)

    # wpa menu item update <id>
    item_update_parser = menu_item_subparsers.add_parser(
        "update", parents=[shared], help="Update a menu item"
    )
    item_update_parser.add_argument("id", type=int, help="Menu item ID")
    item_update_parser.add_argument("--title", help="New link text")
    item_update_parser.add_argument("--url", help="New target URL")
    item_update_parser.add_argument("--parent", type=int, help="New parent item ID")
    item_update_parser.add_argument(
        "--position", type=int, help="New menu order (1-based)"
    )
    item_update_parser.set_defaults(func=_do_menu_item_update)

    # wpa menu item delete <id>
    item_delete_parser = menu_item_subparsers.add_parser(
        "delete", parents=[shared], help="Delete a menu item (always permanent)"
    )
    item_delete_parser.add_argument("id", type=int, help="Menu item ID to delete")
    item_delete_parser.set_defaults(func=_do_menu_item_delete)

    # wpa menu location list
    menu_location_parser = menu_subparsers.add_parser(
        "location", help="Menu location commands"
    )
    menu_location_subparsers = menu_location_parser.add_subparsers(
        dest="menu_location_command"
    )
    location_list_parser = menu_location_subparsers.add_parser(
        "list",
        parents=[shared, list_p],
        help="List registered menu locations (read-only)",
    )
    location_list_parser.set_defaults(func=_do_menu_location_list)

    # --- wpa option ---
    option_parser = subparsers.add_parser(
        "option",
        help="Site settings commands (registered settings only; "
        "requires manage_options capability)",
    )
    option_subparsers = option_parser.add_subparsers(dest="option_command")

    # wpa option list
    option_list_parser = option_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List registered settings"
    )
    option_list_parser.set_defaults(func=_do_option_list)

    # wpa option get <name>
    option_get_parser = option_subparsers.add_parser(
        "get", parents=[shared], help="Get a single setting's value"
    )
    option_get_parser.add_argument("name", help="Setting name (e.g. title)")
    option_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: bare value; json for typed output)",
    )
    option_get_parser.set_defaults(func=_do_option_get)

    # wpa option update <name> <value>
    option_update_parser = option_subparsers.add_parser(
        "update", parents=[shared], help="Update a single setting"
    )
    option_update_parser.add_argument("name", help="Setting name (e.g. title)")
    option_update_parser.add_argument(
        "value",
        help="New value (JSON-parsed when possible: numbers, true/false, null)",
    )
    option_update_parser.set_defaults(func=_do_option_update)

    # --- wpa sidebar ---
    sidebar_parser = subparsers.add_parser(
        "sidebar",
        help="Sidebar commands (requires edit_theme_options capability)",
    )
    sidebar_subparsers = sidebar_parser.add_subparsers(dest="sidebar_command")

    # wpa sidebar list
    sidebar_list_parser = sidebar_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List registered sidebars"
    )
    sidebar_list_parser.set_defaults(func=_do_sidebar_list)

    # --- wpa widget ---
    widget_parser = subparsers.add_parser(
        "widget",
        help="Classic widget commands (requires edit_theme_options capability)",
    )
    widget_subparsers = widget_parser.add_subparsers(dest="widget_command")

    # wpa widget list
    widget_list_parser = widget_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List widgets"
    )
    widget_list_parser.add_argument(
        "--sidebar", help="Filter to one sidebar (e.g. sidebar-1)"
    )
    widget_list_parser.set_defaults(func=_do_widget_list)

    # wpa widget get <id>
    widget_get_parser = widget_subparsers.add_parser(
        "get", parents=[shared], help="Get a single widget"
    )
    widget_get_parser.add_argument("id", help="Widget ID (e.g. recent-posts-3)")
    widget_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    widget_get_parser.set_defaults(func=_do_widget_get)

    # wpa widget update <id>
    widget_update_parser = widget_subparsers.add_parser(
        "update", parents=[shared], help="Move a widget or update its settings"
    )
    widget_update_parser.add_argument("id", help="Widget ID")
    widget_update_parser.add_argument(
        "--sidebar", help="Target sidebar ID (moves the widget)"
    )
    widget_update_parser.add_argument(
        "--instance-json",
        help='Instance settings as a JSON object (e.g. \'{"title": "X"}\')',
    )
    widget_update_parser.set_defaults(func=_do_widget_update)

    # wpa widget deactivate <id>
    widget_deactivate_parser = widget_subparsers.add_parser(
        "deactivate",
        parents=[shared],
        help="Move a widget to the inactive sidebar (settings kept)",
    )
    widget_deactivate_parser.add_argument("id", help="Widget ID")
    widget_deactivate_parser.set_defaults(func=_do_widget_deactivate)

    # wpa widget delete <id>
    widget_delete_parser = widget_subparsers.add_parser(
        "delete", parents=[shared], help="Delete a widget"
    )
    widget_delete_parser.add_argument("id", help="Widget ID")
    widget_delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Remove entirely (default moves to the inactive sidebar)",
    )
    widget_delete_parser.set_defaults(func=_do_widget_delete)

    # --- wpa comment ---
    comment_parser = subparsers.add_parser(
        "comment", help="Comment management commands"
    )
    comment_subparsers = comment_parser.add_subparsers(dest="comment_command")

    # wpa comment list
    comment_list_parser = comment_subparsers.add_parser(
        "list", parents=[shared, list_p], help="List comments"
    )
    comment_list_parser.add_argument("--post", type=int, help="Filter by post ID")
    comment_list_parser.add_argument(
        "--status",
        help="Filter by status (approved, hold, spam, trash)",
    )
    comment_list_parser.add_argument(
        "--parent", type=int, help="Filter by parent comment ID"
    )
    comment_list_parser.add_argument("--author-email", help="Filter by author email")
    comment_list_parser.add_argument("--search", help="Search comments")
    comment_list_parser.add_argument(
        "--per-page", type=int, default=10, help="Results per page (default: 10)"
    )
    comment_list_parser.add_argument("--orderby", help="Sort field (date, id, etc.)")
    comment_list_parser.add_argument(
        "--order", choices=["asc", "desc"], help="Sort order"
    )
    comment_list_parser.set_defaults(func=_do_comment_list)

    # wpa comment get <id>
    comment_get_parser = comment_subparsers.add_parser(
        "get", parents=[shared], help="Get a single comment"
    )
    comment_get_parser.add_argument("id", type=int, help="Comment ID")
    comment_get_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    comment_get_parser.set_defaults(func=_do_comment_get)

    # wpa comment create
    comment_create_parser = comment_subparsers.add_parser(
        "create", parents=[shared], help="Create a new comment"
    )
    comment_create_parser.add_argument(
        "--post", type=int, required=True, help="Post ID being commented on"
    )
    comment_create_parser.add_argument("--content", required=True, help="Comment body")
    comment_create_parser.add_argument("--author-name", help="Author display name")
    comment_create_parser.add_argument("--author-email", help="Author email")
    comment_create_parser.add_argument(
        "--parent", type=int, help="Parent comment ID for replies"
    )
    comment_create_parser.add_argument(
        "--status", help="Comment status (approved, hold, spam)"
    )
    comment_create_parser.set_defaults(func=_do_comment_create)

    # wpa comment update <id>
    comment_update_parser = comment_subparsers.add_parser(
        "update", parents=[shared], help="Update an existing comment"
    )
    comment_update_parser.add_argument("id", type=int, help="Comment ID to update")
    comment_update_parser.add_argument("--content", help="New content")
    comment_update_parser.add_argument("--status", help="New status")
    comment_update_parser.add_argument("--author-name", help="New author display name")
    comment_update_parser.add_argument("--author-email", help="New author email")
    comment_update_parser.set_defaults(func=_do_comment_update)

    # wpa comment delete <id>
    comment_delete_parser = comment_subparsers.add_parser(
        "delete", parents=[shared], help="Delete a comment"
    )
    comment_delete_parser.add_argument("id", type=int, help="Comment ID to delete")
    comment_delete_parser.add_argument(
        "--force", action="store_true", help="Permanently delete (skip trash)"
    )
    comment_delete_parser.set_defaults(func=_do_comment_delete)

    # wpa comment count
    comment_count_parser = comment_subparsers.add_parser(
        "count", parents=[shared], help="Count comments per moderation status"
    )
    comment_count_parser.add_argument(
        "--status",
        choices=list(COMMENT_COUNT_STATUSES),
        help="Count a single status (bare number output)",
    )
    comment_count_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table)",
    )
    comment_count_parser.set_defaults(func=_do_comment_count)

    # Comment moderation subcommands
    for action_name, action_func, help_text in (
        ("approve", _do_comment_approve, "Approve a comment"),
        ("unapprove", _do_comment_unapprove, "Unapprove a comment (mark as held)"),
        ("spam", _do_comment_spam, "Mark a comment as spam"),
        ("unspam", _do_comment_unspam, "Restore a spammed comment"),
        ("trash", _do_comment_trash, "Move a comment to trash"),
    ):
        action_parser = comment_subparsers.add_parser(
            action_name, parents=[shared], help=help_text
        )
        action_parser.add_argument("id", type=int, help="Comment ID")
        action_parser.set_defaults(func=action_func)

    # --- wpa term / category / tag ---
    def _add_term_subparsers(parent_parser, default_taxonomy, allow_taxonomy_flag):
        """Add list/get/create/update/delete subparsers under parent_parser."""
        sub = parent_parser.add_subparsers(
            dest=f"{parent_parser.prog.split()[-1]}_command"
        )

        def _taxonomy_arg(p):
            if allow_taxonomy_flag:
                p.add_argument(
                    "--taxonomy",
                    default=default_taxonomy,
                    help=f"Taxonomy slug (default: {default_taxonomy})",
                )
            else:
                p.set_defaults(taxonomy=default_taxonomy)

        # list
        list_parser_ = sub.add_parser(
            "list", parents=[shared, list_p], help="List terms"
        )
        _taxonomy_arg(list_parser_)
        list_parser_.add_argument("--search", help="Search terms")
        list_parser_.add_argument("--parent", type=int, help="Filter by parent term ID")
        list_parser_.add_argument(
            "--hide-empty",
            action="store_true",
            help="Hide terms with no associated posts",
        )
        list_parser_.add_argument(
            "--per-page",
            type=int,
            default=100,
            help="Results per page (default: 100)",
        )
        list_parser_.add_argument(
            "--orderby", help="Sort field (name, slug, count, id)"
        )
        list_parser_.add_argument("--order", choices=["asc", "desc"], help="Sort order")
        list_parser_.set_defaults(func=_do_term_list)

        # get
        get_parser_ = sub.add_parser("get", parents=[shared], help="Get a single term")
        get_parser_.add_argument("id", type=int, help="Term ID")
        _taxonomy_arg(get_parser_)
        get_parser_.add_argument(
            "--format",
            default="table",
            choices=["table", "json"],
            help="Output format (default: table)",
        )
        get_parser_.set_defaults(func=_do_term_get)

        # create
        create_parser_ = sub.add_parser(
            "create", parents=[shared], help="Create a new term"
        )
        create_parser_.add_argument("--name", required=True, help="Term name")
        _taxonomy_arg(create_parser_)
        create_parser_.add_argument("--slug", help="URL slug")
        create_parser_.add_argument("--description", help="Term description")
        create_parser_.add_argument(
            "--parent", type=int, help="Parent term ID (hierarchical taxonomies)"
        )
        create_parser_.set_defaults(func=_do_term_create)

        # update
        update_parser_ = sub.add_parser(
            "update", parents=[shared], help="Update an existing term"
        )
        update_parser_.add_argument("id", type=int, help="Term ID to update")
        _taxonomy_arg(update_parser_)
        update_parser_.add_argument("--name", help="New name")
        update_parser_.add_argument("--slug", help="New slug")
        update_parser_.add_argument("--description", help="New description")
        update_parser_.add_argument("--parent", type=int, help="New parent term ID")
        update_parser_.set_defaults(func=_do_term_update)

        # delete
        delete_parser_ = sub.add_parser(
            "delete",
            parents=[shared],
            help="Delete a term (always permanent — terms cannot be trashed)",
        )
        delete_parser_.add_argument("id", type=int, help="Term ID to delete")
        _taxonomy_arg(delete_parser_)
        delete_parser_.set_defaults(func=_do_term_delete)

        return sub

    term_parser = subparsers.add_parser(
        "term", help="Taxonomy term management (categories, tags, custom taxonomies)"
    )
    _add_term_subparsers(
        term_parser, default_taxonomy="category", allow_taxonomy_flag=True
    )

    category_parser = subparsers.add_parser(
        "category", help="Category management (alias for 'term --taxonomy=category')"
    )
    _add_term_subparsers(
        category_parser, default_taxonomy="category", allow_taxonomy_flag=False
    )

    tag_parser = subparsers.add_parser(
        "tag", help="Tag management (alias for 'term --taxonomy=post_tag')"
    )
    _add_term_subparsers(
        tag_parser, default_taxonomy="post_tag", allow_taxonomy_flag=False
    )

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

    if args.command == "comment" and not args.comment_command:  # pragma: no cover
        comment_parser.print_help()
        return 1

    if args.command == "term" and not getattr(
        args, "term_command", None
    ):  # pragma: no cover
        term_parser.print_help()
        return 1

    if args.command == "category" and not getattr(
        args, "category_command", None
    ):  # pragma: no cover
        category_parser.print_help()
        return 1

    if args.command == "tag" and not getattr(
        args, "tag_command", None
    ):  # pragma: no cover
        tag_parser.print_help()
        return 1

    if args.command == "taxonomy" and not getattr(
        args, "taxonomy_command", None
    ):  # pragma: no cover
        taxonomy_parser.print_help()
        return 1

    if args.command == "post-type" and not getattr(
        args, "post_type_command", None
    ):  # pragma: no cover
        post_type_parser.print_help()
        return 1

    if args.command == "block" and not getattr(
        args, "block_command", None
    ):  # pragma: no cover
        block_parser.print_help()
        return 1

    if args.command == "theme" and not getattr(
        args, "theme_command", None
    ):  # pragma: no cover
        theme_parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
