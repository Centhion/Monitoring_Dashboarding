#!/usr/bin/env python3
"""
Lansweeper-to-Monitoring Inventory Sync

Queries the Lansweeper Cloud GraphQL API and synchronizes asset data into
the monitoring stack's inventory/hosts.yml. Supports dry-run mode, configurable
field mapping, and rate-limit-aware pagination.

Subcommands:
    sync             -- Pull assets from Lansweeper and merge into hosts.yml
    list-sites       -- List authorized Lansweeper sites (useful for finding site IDs)

Environment Variables:
    LANSWEEPER_API_URL     -- GraphQL endpoint (default: https://api.lansweeper.com/api/v2/graphql)
    LANSWEEPER_SITE_ID     -- Target site ID
    LANSWEEPER_PAT         -- Personal Access Token for authentication

Exit codes:
    0 -- Success
    1 -- Runtime error or configuration issue

Usage:
    python3 scripts/lansweeper_sync.py list-sites
    python3 scripts/lansweeper_sync.py sync --dry-run
    python3 scripts/lansweeper_sync.py sync

Dependencies:
    - PyYAML (pyyaml)
    - urllib3 / http.client (stdlib)
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install it with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS_PATH = REPO_ROOT / "inventory" / "hosts.yml"
FIELD_MAP_PATH = REPO_ROOT / "inventory" / "lansweeper_field_map.yml"

DEFAULT_API_URL = "https://api.lansweeper.com/api/v2/graphql"
PAGE_SIZE = 500  # Lansweeper max per request
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 65  # Must exceed the 60-second rate-limit cooldown


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------


def load_env_config() -> dict:
    """Load and validate Lansweeper connection settings from environment.

    Returns a dict with keys: api_url, site_id, pat.
    Exits with an error if required variables are missing.
    """
    api_url = os.environ.get("LANSWEEPER_API_URL", DEFAULT_API_URL)
    site_id = os.environ.get("LANSWEEPER_SITE_ID", "")
    pat = os.environ.get("LANSWEEPER_PAT", "")

    missing = []
    if not site_id:
        missing.append("LANSWEEPER_SITE_ID")
    if not pat:
        missing.append("LANSWEEPER_PAT")

    if missing:
        print(
            f"ERROR: Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            "  Set them in your .env file or export them before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    return {"api_url": api_url, "site_id": site_id, "pat": pat}


def load_field_map(path: Path = FIELD_MAP_PATH) -> dict:
    """Load the Lansweeper field mapping configuration.

    Returns the parsed YAML as a dict with defaults applied for missing keys.
    """
    if not path.exists():
        print(f"ERROR: Field map not found: {path}", file=sys.stderr)
        print("  Expected at: inventory/lansweeper_field_map.yml", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # Apply defaults for optional keys
    data.setdefault("include_asset_types", [])
    data.setdefault("exclude_asset_types", [])
    data.setdefault("default_role", "generic")
    data.setdefault("role_rules", [])
    data.setdefault("default_site", "unknown")
    if data.get("site_rules") is None:
        data["site_rules"] = []
    data.setdefault("os_map", {"Windows": "windows", "Linux": "linux"})
    data.setdefault(
        "sync_fields",
        [
            "assetBasicInfo.name",
            "assetBasicInfo.ipAddress",
            "assetBasicInfo.type",
        ],
    )

    return data


def load_existing_hosts(path: Path = HOSTS_PATH) -> dict:
    """Load the current hosts.yml inventory.

    Returns a dict of hostname -> attributes. Returns empty dict if the file
    contains only template comments.
    """
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return data.get("hosts") or {}


# ---------------------------------------------------------------------------
# GraphQL client
# ---------------------------------------------------------------------------


def graphql_request(
    api_url: str, pat: str, query: str, variables: dict | None = None
) -> dict:
    """Execute a GraphQL request against the Lansweeper API.

    Handles rate limiting with exponential backoff. The Lansweeper rate limiter
    blocks all requests for a full minute after the limit is hit, and any
    request during that cooldown resets the timer. So we wait the full
    cooldown period plus jitter before retrying.

    Returns the parsed JSON response body.
    Raises RuntimeError on persistent failures.
    """
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {pat}",
    }

    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(
            api_url, data=body, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))

            # Check for GraphQL-level errors
            if "errors" in response_data:
                errors = response_data["errors"]
                error_messages = [e.get("message", str(e)) for e in errors]

                # Rate limit errors require backoff
                rate_limited = any(
                    "rate" in msg.lower() or "throttl" in msg.lower()
                    for msg in error_messages
                )
                if rate_limited and attempt < MAX_RETRIES - 1:
                    wait = BACKOFF_BASE_SECONDS * (attempt + 1)
                    print(
                        f"  Rate limited. Waiting {wait}s before retry "
                        f"({attempt + 1}/{MAX_RETRIES})..."
                    )
                    time.sleep(wait)
                    continue

                raise RuntimeError(
                    f"GraphQL errors: {'; '.join(error_messages)}"
                )

            return response_data

        except urllib.error.HTTPError as exc:
            # HTTP 429 Too Many Requests
            if exc.code == 429 and attempt < MAX_RETRIES - 1:
                wait = BACKOFF_BASE_SECONDS * (attempt + 1)
                print(
                    f"  HTTP 429 rate limited. Waiting {wait}s before retry "
                    f"({attempt + 1}/{MAX_RETRIES})..."
                )
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"HTTP {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Connection error: {exc.reason}"
            ) from exc

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries")


# ---------------------------------------------------------------------------
# API queries
# ---------------------------------------------------------------------------


def query_authorized_sites(api_url: str, pat: str) -> list[dict]:
    """List all Lansweeper sites the API client is authorized to access.

    Returns a list of dicts with 'id' and 'name' keys.
    """
    query = """
    {
        authorizedSites {
            sites {
                id
                name
            }
        }
    }
    """
    result = graphql_request(api_url, pat, query)
    sites = result.get("data", {}).get("authorizedSites", {}).get("sites", [])
    return sites


def query_assets_page(
    api_url: str,
    pat: str,
    site_id: str,
    fields: list[str],
    page_cursor: str = "FIRST",
    include_types: list[str] | None = None,
) -> dict:
    """Query a single page of asset resources from Lansweeper.

    Args:
        page_cursor: Pagination cursor -- "FIRST" for the first page,
                     or a cursor string for subsequent pages.
        include_types: Optional list of asset types to filter by.

    Returns the raw assetResources response dict with keys:
        total (first page only), items, pagination.
    """
    # Build filters for asset type if specified
    filters_clause = ""
    if include_types:
        # Lansweeper uses conditions with operator/value for filtering
        type_values = json.dumps(include_types)
        filters_clause = f"""
            filters: {{
                conjunction: OR
                conditions: [
                    {{
                        path: "assetBasicInfo.type"
                        operator: EQUAL
                        value: {type_values}
                    }}
                ]
            }}
        """

    # Determine pagination parameters
    if page_cursor == "FIRST":
        pagination_clause = f'assetPagination: {{ limit: {PAGE_SIZE}, page: FIRST }}'
    else:
        pagination_clause = (
            f'assetPagination: {{ limit: {PAGE_SIZE}, page: NEXT, '
            f'cursor: "{page_cursor}" }}'
        )

    # Build fields array string
    fields_str = json.dumps(fields)

    query = f"""
    {{
        site(id: "{site_id}") {{
            assetResources(
                {pagination_clause}
                fields: {fields_str}
                {filters_clause}
            ) {{
                total
                items
                pagination {{
                    limit
                    current
                    next
                    page
                }}
            }}
        }}
    }}
    """

    result = graphql_request(api_url, pat, query)

    site_data = result.get("data", {}).get("site", {})
    if not site_data:
        raise RuntimeError(
            f"No data returned for site '{site_id}'. "
            "Verify the site ID with: lansweeper_sync.py list-sites"
        )

    return site_data.get("assetResources", {})


def fetch_all_assets(
    api_url: str,
    pat: str,
    site_id: str,
    fields: list[str],
    include_types: list[str] | None = None,
) -> list[dict]:
    """Fetch all assets across paginated results.

    Handles the Lansweeper pagination quirk where 'total' is only available
    on the first page request. Iterates through all pages using cursor-based
    pagination.

    Returns a flat list of asset item dicts.
    """
    all_items = []

    # First page -- includes total count
    print("  Querying Lansweeper assets (page 1)...")
    first_page = query_assets_page(
        api_url, pat, site_id, fields,
        page_cursor="FIRST",
        include_types=include_types,
    )

    total = first_page.get("total", 0)
    items = first_page.get("items", [])
    pagination = first_page.get("pagination", {})

    all_items.extend(items)
    print(f"  Total assets: {total} | Fetched: {len(all_items)}")

    # Subsequent pages
    page_num = 1
    while pagination.get("next"):
        page_num += 1
        cursor = pagination["next"]
        print(f"  Fetching page {page_num}...")

        page_data = query_assets_page(
            api_url, pat, site_id, fields,
            page_cursor=cursor,
            include_types=include_types,
        )

        items = page_data.get("items", [])
        pagination = page_data.get("pagination", {})
        all_items.extend(items)
        print(f"  Fetched: {len(all_items)} / {total}")

    return all_items


# ---------------------------------------------------------------------------
# Asset-to-host mapping
# ---------------------------------------------------------------------------


def extract_field(asset: dict, dotpath: str) -> str | None:
    """Extract a value from a Lansweeper asset item using a dot-notation path.

    Lansweeper returns items as flat dicts with dot-notation keys matching the
    requested fields. For example, requesting "assetBasicInfo.name" returns
    an item like: {"assetBasicInfo.name": "SRV-WEB-01"}.

    Returns the string value or None if not present.
    """
    # Lansweeper items use the field path as the key directly
    value = asset.get(dotpath)
    if value is None:
        # Also try nested dict traversal as a fallback
        parts = dotpath.split(".")
        current = asset
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        value = current

    if value is None:
        return None
    return str(value).strip() if value else None


def match_role(asset: dict, field_map: dict) -> str:
    """Determine the monitoring role for an asset based on field mapping rules.

    Evaluates role_rules in order; first match wins. Falls back to default_role.
    """
    hostname = extract_field(asset, "assetBasicInfo.name") or ""

    for rule in field_map.get("role_rules", []):
        match_criteria = rule.get("match", {})
        matched = True

        # Check name_regex
        if "name_regex" in match_criteria:
            pattern = match_criteria["name_regex"]
            if not re.match(pattern, hostname, re.IGNORECASE):
                matched = False

        # Check asset_type
        if "asset_type" in match_criteria and matched:
            asset_type = extract_field(asset, "assetBasicInfo.type") or ""
            if asset_type.lower() != match_criteria["asset_type"].lower():
                matched = False

        # Check description
        if "description_match" in match_criteria and matched:
            desc = extract_field(asset, "assetCustom.description") or ""
            if match_criteria["description_match"].lower() not in desc.lower():
                matched = False

        if matched:
            return rule["role"]

    return field_map.get("default_role", "generic")


def match_site(asset: dict, field_map: dict) -> str:
    """Determine the monitoring site for an asset based on field mapping rules.

    Evaluates site_rules in order; first match wins. Falls back to default_site.
    """
    for rule in field_map.get("site_rules", []):
        match_criteria = rule.get("match", {})
        matched = True

        # Check location substring
        if "location" in match_criteria:
            location = extract_field(asset, "assetCustom.location") or ""
            if match_criteria["location"].lower() not in location.lower():
                matched = False

        # Check IP prefix
        if "ip_prefix" in match_criteria and matched:
            ip_addr = extract_field(asset, "assetBasicInfo.ipAddress") or ""
            if not ip_addr.startswith(match_criteria["ip_prefix"]):
                matched = False

        # Check network regex
        if "network_regex" in match_criteria and matched:
            ip_addr = extract_field(asset, "assetBasicInfo.ipAddress") or ""
            if not re.match(match_criteria["network_regex"], ip_addr):
                matched = False

        # Check FQDN suffix
        if "fqdn_suffix" in match_criteria and matched:
            fqdn = extract_field(asset, "assetBasicInfo.fqdn") or ""
            if not fqdn.lower().endswith(match_criteria["fqdn_suffix"].lower()):
                matched = False

        if matched:
            return rule["site"]

    return field_map.get("default_site", "unknown")


def map_asset_to_host(asset: dict, field_map: dict) -> tuple[str | None, dict | None]:
    """Convert a Lansweeper asset into a hosts.yml entry.

    Returns (hostname, host_dict) or (None, None) if the asset should be skipped.
    """
    hostname = extract_field(asset, "assetBasicInfo.name")
    if not hostname:
        return None, None

    # Normalize hostname to lowercase for consistency
    hostname = hostname.lower()

    # Determine asset type and check exclusions
    asset_type = extract_field(asset, "assetBasicInfo.type") or ""
    exclude_types = [t.lower() for t in field_map.get("exclude_asset_types", [])]
    if asset_type.lower() in exclude_types:
        return None, None

    # Map OS from asset type
    os_map = field_map.get("os_map", {})
    host_os = os_map.get(asset_type, None)
    if not host_os:
        # Try case-insensitive lookup
        for key, value in os_map.items():
            if key.lower() == asset_type.lower():
                host_os = value
                break
    if not host_os:
        host_os = asset_type.lower() if asset_type else "unknown"

    # Map role and site
    role = match_role(asset, field_map)
    site = match_site(asset, field_map)

    # Build the host entry matching hosts.yml schema
    ip_addr = extract_field(asset, "assetBasicInfo.ipAddress")
    fqdn = extract_field(asset, "assetBasicInfo.fqdn")

    host_entry = {
        "site": site,
        "roles": [role],
        "os": host_os,
        "ip": ip_addr,
    }

    # Add useful metadata as notes
    notes_parts = []
    manufacturer = extract_field(asset, "assetCustom.manufacturer")
    model = extract_field(asset, "assetCustom.model")
    serial = extract_field(asset, "assetCustom.serialNumber")
    if manufacturer and model:
        notes_parts.append(f"{manufacturer} {model}")
    elif model:
        notes_parts.append(model)
    if serial:
        notes_parts.append(f"S/N: {serial}")
    if fqdn:
        notes_parts.append(f"FQDN: {fqdn}")

    if notes_parts:
        host_entry["notes"] = " | ".join(notes_parts)

    # Tag the entry as Lansweeper-managed for merge tracking
    host_entry["source"] = "lansweeper"

    return hostname, host_entry


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------


def merge_hosts(
    existing: dict, incoming: dict, dry_run: bool = False
) -> tuple[dict, dict]:
    """Merge Lansweeper-sourced hosts into existing inventory.

    Merge strategy:
    - New hosts (not in existing): added
    - Existing hosts with source=lansweeper: updated with fresh data
    - Existing hosts without source=lansweeper (manually added): never overwritten
    - Hosts in existing with source=lansweeper but NOT in incoming: flagged as
      potentially decommissioned (logged but not removed)

    Returns (merged_hosts, change_summary) where change_summary has keys:
        added, updated, skipped_manual, stale
    """
    merged = dict(existing)
    changes = {"added": [], "updated": [], "skipped_manual": [], "stale": []}

    # Track which Lansweeper-managed hosts are still present in the API
    incoming_hostnames = set(incoming.keys())
    existing_ls_hosts = {
        name for name, attrs in existing.items()
        if isinstance(attrs, dict) and attrs.get("source") == "lansweeper"
    }

    for hostname, host_data in incoming.items():
        if hostname in existing:
            existing_entry = existing[hostname]
            if isinstance(existing_entry, dict) and existing_entry.get("source") == "lansweeper":
                # Lansweeper-managed host: safe to update
                if not dry_run:
                    merged[hostname] = host_data
                changes["updated"].append(hostname)
            else:
                # Manually managed host: do not overwrite
                changes["skipped_manual"].append(hostname)
        else:
            # New host from Lansweeper
            if not dry_run:
                merged[hostname] = host_data
            changes["added"].append(hostname)

    # Identify Lansweeper hosts no longer returned by the API
    stale = existing_ls_hosts - incoming_hostnames
    changes["stale"] = sorted(stale)

    return merged, changes


def write_hosts(hosts: dict, path: Path = HOSTS_PATH) -> None:
    """Write the merged host inventory back to hosts.yml."""
    header = (
        "# Host Inventory -- Server and Device Registry\n"
        "# Managed by: scripts/lansweeper_sync.py and manual entries\n"
        "# Entries with 'source: lansweeper' are auto-synced and will be\n"
        "# updated on next sync. Manual entries are never overwritten.\n"
        "#\n"
        "# Validate after sync:\n"
        "#   python3 scripts/fleet_inventory.py validate\n\n"
    )

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.dump({"hosts": hosts}, fh, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_list_sites(args: argparse.Namespace) -> int:
    """List all Lansweeper sites the API client can access."""
    # list-sites only needs the PAT, not the site ID
    api_url = os.environ.get("LANSWEEPER_API_URL", DEFAULT_API_URL)
    pat = os.environ.get("LANSWEEPER_PAT", "")

    if not pat:
        print(
            "ERROR: LANSWEEPER_PAT environment variable is required.",
            file=sys.stderr,
        )
        return 1

    print(f"Querying authorized sites at {api_url}...")
    try:
        sites = query_authorized_sites(api_url, pat)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("No authorized sites found. Check your API client permissions.")
        return 0

    print(f"\nAuthorized Sites ({len(sites)}):")
    print("-" * 60)
    for site in sites:
        print(f"  ID:   {site.get('id', 'N/A')}")
        print(f"  Name: {site.get('name', 'N/A')}")
        print()

    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync assets from Lansweeper into hosts.yml."""
    config = load_env_config()
    field_map = load_field_map()
    dry_run = args.dry_run

    if dry_run:
        print("=== DRY RUN === (no changes will be written)")
    print(f"Syncing from Lansweeper site: {config['site_id']}")
    print(f"API endpoint: {config['api_url']}")
    print()

    # Fetch assets from Lansweeper
    include_types = field_map.get("include_asset_types") or None
    sync_fields = field_map.get("sync_fields", [])

    try:
        raw_assets = fetch_all_assets(
            config["api_url"],
            config["pat"],
            config["site_id"],
            sync_fields,
            include_types=include_types,
        )
    except RuntimeError as exc:
        print(f"ERROR: Failed to fetch assets: {exc}", file=sys.stderr)
        return 1

    print(f"\nReceived {len(raw_assets)} assets from Lansweeper")

    # Map assets to hosts.yml schema
    incoming_hosts = {}
    skipped_count = 0

    for asset in raw_assets:
        hostname, host_data = map_asset_to_host(asset, field_map)
        if hostname and host_data:
            incoming_hosts[hostname] = host_data
        else:
            skipped_count += 1

    print(f"Mapped {len(incoming_hosts)} assets to host entries ({skipped_count} skipped)")

    if not incoming_hosts:
        print("No hosts to sync. Check your field mapping configuration.")
        return 0

    # Load existing inventory and merge
    existing_hosts = load_existing_hosts()
    merged, changes = merge_hosts(existing_hosts, incoming_hosts, dry_run=dry_run)

    # Report changes
    print("\n" + "=" * 60)
    print("  Sync Summary")
    print("=" * 60)

    if changes["added"]:
        print(f"\n  NEW ({len(changes['added'])}):")
        for name in sorted(changes["added"]):
            host = incoming_hosts[name]
            print(f"    + {name}  [{host['os']}] [{host['roles'][0]}] [{host['site']}]")

    if changes["updated"]:
        print(f"\n  UPDATED ({len(changes['updated'])}):")
        for name in sorted(changes["updated"]):
            print(f"    ~ {name}")

    if changes["skipped_manual"]:
        print(f"\n  SKIPPED (manually managed) ({len(changes['skipped_manual'])}):")
        for name in sorted(changes["skipped_manual"]):
            print(f"    - {name}")

    if changes["stale"]:
        print(f"\n  STALE (in hosts.yml but not in Lansweeper) ({len(changes['stale'])}):")
        for name in changes["stale"]:
            print(f"    ? {name}")

    total_changes = len(changes["added"]) + len(changes["updated"])
    if total_changes == 0:
        print("\n  No changes to apply.")
        return 0

    if dry_run:
        print(f"\n  DRY RUN: {total_changes} change(s) would be applied.")
        print("  Run without --dry-run to apply.")
        return 0

    # Write merged inventory
    write_hosts(merged)
    print(f"\n  Applied {total_changes} change(s) to {HOSTS_PATH}")
    print("  Run validation: python3 scripts/fleet_inventory.py validate")

    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        description="Sync Lansweeper asset inventory into the monitoring stack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/lansweeper_sync.py list-sites\n"
            "  python3 scripts/lansweeper_sync.py sync --dry-run\n"
            "  python3 scripts/lansweeper_sync.py sync\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-sites
    subparsers.add_parser(
        "list-sites",
        help="List authorized Lansweeper sites",
    )

    # sync
    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync Lansweeper assets into hosts.yml",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to hosts.yml",
    )

    args = parser.parse_args()

    dispatch = {
        "list-sites": cmd_list_sites,
        "sync": cmd_sync,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
