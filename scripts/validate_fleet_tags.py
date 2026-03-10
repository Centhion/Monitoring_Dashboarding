#!/usr/bin/env python3
"""
Fleet Tag Validator -- Cross-Reference Prometheus Labels Against Inventory

Queries a live Prometheus instance for all reporting hosts and compares their
labels (hostname, datacenter, role, os) against the inventory defined in
inventory/hosts.yml. Identifies compliance drift, missing hosts, and unknown
hosts that report metrics but are not tracked in inventory.

Categories:
    COMPLIANT -- Host is in inventory and all Prometheus labels match
    DRIFT     -- Host is in inventory but one or more labels differ
    MISSING   -- Host is in inventory but not reporting to Prometheus
    UNKNOWN   -- Host reports to Prometheus but is not in inventory

Usage:
    python3 scripts/validate_fleet_tags.py
    python3 scripts/validate_fleet_tags.py --prometheus-url http://prometheus:9090
    python3 scripts/validate_fleet_tags.py --site site-alpha --format json
    python3 scripts/validate_fleet_tags.py --role sql --format csv

Environment variables:
    PROMETHEUS_URL -- Default Prometheus base URL (overridden by --prometheus-url)

Dependencies:
    - PyYAML (pyyaml)
    - Python 3.9+ (stdlib only for HTTP: urllib.request)

Exit codes:
    0 -- All hosts compliant (or no hosts defined)
    1 -- Drift, missing, or unknown hosts detected
    2 -- Runtime error (connection failure, bad response, etc.)
"""

import argparse
import json
import os
import sys
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
    sys.exit(2)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS_PATH = REPO_ROOT / "inventory" / "hosts.yml"

# The Prometheus metric used to discover host labels. This should be a metric
# that every Alloy agent exports. windows_os_info and node_uname_info are
# common choices; we query both and merge results.
DISCOVERY_METRICS = [
    "windows_os_info",
    "node_uname_info",
]

# Label names on the Prometheus side that correspond to inventory fields.
# Adjust these if your Alloy config uses different label names.
LABEL_MAP = {
    "hostname": "instance_hostname",  # or "hostname" depending on relabel config
    "datacenter": "datacenter",
    "role": "role",
    "os": "os",
}


# ---------------------------------------------------------------------------
# Inventory loading
# ---------------------------------------------------------------------------


def load_inventory(path: Path = HOSTS_PATH) -> dict:
    """Load hosts.yml and return the hosts dict.

    Returns an empty dict if the file is an empty template.
    """
    if not path.exists():
        print(f"ERROR: Inventory file not found: {path}", file=sys.stderr)
        sys.exit(2)

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return data.get("hosts") or {}


# ---------------------------------------------------------------------------
# Prometheus query helpers
# ---------------------------------------------------------------------------


def query_prometheus_series(base_url: str, metric_name: str) -> list[dict]:
    """Query Prometheus /api/v1/series for a given metric and return label sets.

    Each element in the returned list is a dict of label key-value pairs
    representing one unique time series.
    """
    url = f"{base_url.rstrip('/')}/api/v1/series"
    params = urllib.parse.urlencode({"match[]": metric_name})
    full_url = f"{url}?{params}"

    try:
        req = urllib.request.Request(full_url, method="GET")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"ERROR: Failed to query Prometheus at {full_url}: {exc}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON response from Prometheus: {exc}", file=sys.stderr)
        sys.exit(2)

    if body.get("status") != "success":
        print(f"ERROR: Prometheus returned status '{body.get('status')}': {body.get('error', 'unknown')}", file=sys.stderr)
        sys.exit(2)

    return body.get("data", [])


# Need urllib.parse for URL encoding
import urllib.parse  # noqa: E402 -- grouped with urllib usage above


def discover_reporting_hosts(base_url: str) -> dict[str, dict]:
    """Query Prometheus for all hosts reporting metrics.

    Returns a dict keyed by hostname, where each value contains the
    discovered labels: datacenter, role, os.
    """
    discovered: dict[str, dict] = {}

    for metric in DISCOVERY_METRICS:
        series_list = query_prometheus_series(base_url, metric)

        for labels in series_list:
            # Extract hostname from configured label (fall back to 'instance')
            hostname = (
                labels.get(LABEL_MAP["hostname"])
                or labels.get("hostname")
                or labels.get("instance", "")
            )

            # Strip port suffix from instance label if present
            if ":" in hostname:
                hostname = hostname.split(":")[0]

            if not hostname:
                continue

            discovered[hostname] = {
                "datacenter": labels.get(LABEL_MAP["datacenter"], ""),
                "role": labels.get(LABEL_MAP["role"], ""),
                "os": labels.get(LABEL_MAP["os"], ""),
            }

    return discovered


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------


def compare_fleet(
    inventory: dict,
    discovered: dict,
    filter_site: str | None = None,
    filter_role: str | None = None,
) -> dict[str, list[dict]]:
    """Compare inventory against discovered hosts and classify each.

    Returns a dict with keys: compliant, drift, missing, unknown.
    Each value is a list of dicts describing the host and any discrepancies.
    """
    results: dict[str, list[dict]] = {
        "compliant": [],
        "drift": [],
        "missing": [],
        "unknown": [],
    }

    # Normalize inventory for comparison
    inventory_lookup: dict[str, dict] = {}
    for hostname, attrs in inventory.items():
        if not isinstance(attrs, dict):
            continue

        # Apply filters
        if filter_site and attrs.get("site") != filter_site:
            continue
        if filter_role and filter_role not in (attrs.get("roles") or []):
            continue

        inventory_lookup[hostname] = {
            "site": attrs.get("site", ""),
            "roles": attrs.get("roles") or [],
            "os": attrs.get("os", ""),
        }

    # Check each inventory host against Prometheus data
    for hostname, inv_attrs in inventory_lookup.items():
        if hostname not in discovered:
            results["missing"].append({
                "hostname": hostname,
                "inventory_site": inv_attrs["site"],
                "inventory_roles": inv_attrs["roles"],
                "inventory_os": inv_attrs["os"],
            })
            continue

        prom = discovered[hostname]
        diffs: list[str] = []

        # Compare datacenter/site
        if prom["datacenter"] and prom["datacenter"] != inv_attrs["site"]:
            diffs.append(f"site: inventory='{inv_attrs['site']}' prometheus='{prom['datacenter']}'")

        # Compare OS
        if prom["os"] and prom["os"] != inv_attrs["os"]:
            diffs.append(f"os: inventory='{inv_attrs['os']}' prometheus='{prom['os']}'")

        # Compare role (Prometheus may only have one role label; check membership)
        if prom["role"] and prom["role"] not in inv_attrs["roles"]:
            diffs.append(f"role: inventory={inv_attrs['roles']} prometheus='{prom['role']}'")

        if diffs:
            results["drift"].append({
                "hostname": hostname,
                "differences": diffs,
            })
        else:
            results["compliant"].append({"hostname": hostname})

    # Find unknown hosts (in Prometheus but not in inventory)
    for hostname in discovered:
        if hostname not in inventory_lookup:
            # Only include if not filtered out by site/role constraints
            prom = discovered[hostname]
            if filter_site and prom.get("datacenter") != filter_site:
                continue
            if filter_role and prom.get("role") != filter_role:
                continue

            results["unknown"].append({
                "hostname": hostname,
                "prometheus_datacenter": prom["datacenter"],
                "prometheus_role": prom["role"],
                "prometheus_os": prom["os"],
            })

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_table(results: dict[str, list[dict]]) -> str:
    """Format comparison results as a human-readable table."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("  Fleet Tag Validation Report")
    lines.append("=" * 72)

    # Summary counts
    lines.append("")
    lines.append(f"  COMPLIANT : {len(results['compliant']):>4} host(s)")
    lines.append(f"  DRIFT     : {len(results['drift']):>4} host(s)")
    lines.append(f"  MISSING   : {len(results['missing']):>4} host(s)")
    lines.append(f"  UNKNOWN   : {len(results['unknown']):>4} host(s)")

    # Drift details
    if results["drift"]:
        lines.append("")
        lines.append("  DRIFT Details:")
        lines.append("  " + "-" * 60)
        for entry in results["drift"]:
            lines.append(f"    {entry['hostname']}:")
            for diff in entry["differences"]:
                lines.append(f"      - {diff}")

    # Missing details
    if results["missing"]:
        lines.append("")
        lines.append("  MISSING Hosts (in inventory, not reporting):")
        lines.append("  " + "-" * 60)
        for entry in results["missing"]:
            roles_str = ", ".join(entry["inventory_roles"])
            lines.append(
                f"    {entry['hostname']:<30} site={entry['inventory_site']}"
                f"  roles=[{roles_str}]  os={entry['inventory_os']}"
            )

    # Unknown details
    if results["unknown"]:
        lines.append("")
        lines.append("  UNKNOWN Hosts (reporting but not in inventory):")
        lines.append("  " + "-" * 60)
        for entry in results["unknown"]:
            lines.append(
                f"    {entry['hostname']:<30} dc={entry['prometheus_datacenter']}"
                f"  role={entry['prometheus_role']}  os={entry['prometheus_os']}"
            )

    lines.append("")
    return "\n".join(lines)


def format_json(results: dict[str, list[dict]]) -> str:
    """Format comparison results as JSON."""
    return json.dumps(results, indent=2)


def format_csv(results: dict[str, list[dict]]) -> str:
    """Format comparison results as CSV rows."""
    lines: list[str] = ["status,hostname,details"]

    for entry in results["compliant"]:
        lines.append(f"COMPLIANT,{entry['hostname']},")

    for entry in results["drift"]:
        details = "; ".join(entry["differences"]).replace(",", " ")
        lines.append(f"DRIFT,{entry['hostname']},{details}")

    for entry in results["missing"]:
        roles_str = ";".join(entry["inventory_roles"])
        details = f"site={entry['inventory_site']} roles=[{roles_str}] os={entry['inventory_os']}"
        lines.append(f"MISSING,{entry['hostname']},{details}")

    for entry in results["unknown"]:
        details = (
            f"dc={entry['prometheus_datacenter']} "
            f"role={entry['prometheus_role']} "
            f"os={entry['prometheus_os']}"
        )
        lines.append(f"UNKNOWN,{entry['hostname']},{details}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run the fleet tag validation."""
    parser = argparse.ArgumentParser(
        description="Validate fleet host tags against live Prometheus labels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/validate_fleet_tags.py\n"
            "  python3 scripts/validate_fleet_tags.py --prometheus-url http://prom:9090\n"
            "  python3 scripts/validate_fleet_tags.py --site site-alpha --format json\n"
            "  python3 scripts/validate_fleet_tags.py --role sql --format csv\n"
        ),
    )

    default_prom_url = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
    parser.add_argument(
        "--prometheus-url",
        default=default_prom_url,
        help=f"Prometheus base URL (default: {default_prom_url})",
    )
    parser.add_argument(
        "--site",
        default=None,
        help="Filter to a specific site code (e.g., site-alpha)",
    )
    parser.add_argument(
        "--role",
        default=None,
        help="Filter to a specific role (e.g., sql, dc, iis)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        dest="output_format",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    # Load inventory
    inventory = load_inventory()
    if not inventory:
        print("No hosts defined in inventory/hosts.yml. Nothing to validate.")
        sys.exit(0)

    # Query Prometheus
    discovered = discover_reporting_hosts(args.prometheus_url)

    # Compare
    results = compare_fleet(
        inventory,
        discovered,
        filter_site=args.site,
        filter_role=args.role,
    )

    # Format and output
    formatters = {
        "table": format_table,
        "json": format_json,
        "csv": format_csv,
    }

    print(formatters[args.output_format](results))

    # Exit code: 0 if fully compliant, 1 if any issues found
    has_issues = results["drift"] or results["missing"] or results["unknown"]
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
