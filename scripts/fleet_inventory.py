#!/usr/bin/env python3
"""
Fleet Inventory Management Tool

Validates, reports on, and imports host inventory for the monitoring fleet.
Works with the YAML-based inventory schema in inventory/sites.yml and
inventory/hosts.yml.

Subcommands:
    validate          -- Check sites.yml and hosts.yml for structural errors
    report            -- Print summary tables (hosts by site, role, OS)
    import            -- Import hosts from a CSV file into hosts.yml
    ansible-inventory -- Generate Ansible inventory YAML from hosts.yml

Exit codes:
    0 -- Success (or validation passed with no errors)
    1 -- Validation errors found or runtime failure

Usage:
    python3 scripts/fleet_inventory.py validate
    python3 scripts/fleet_inventory.py report
    python3 scripts/fleet_inventory.py import --csv hosts.csv
    python3 scripts/fleet_inventory.py ansible-inventory > ansible/inventory.yml

Dependencies:
    - PyYAML (pyyaml)
"""

import argparse
import csv
import os
import sys
from collections import Counter
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
SITES_PATH = REPO_ROOT / "inventory" / "sites.yml"
HOSTS_PATH = REPO_ROOT / "inventory" / "hosts.yml"


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------


def load_sites(path: Path = SITES_PATH) -> dict:
    """Load and return parsed sites.yml content.

    Returns a dict with keys 'valid_roles', 'valid_os', and 'sites'.
    Handles the empty-template case where top-level keys exist but map to None.
    """
    if not path.exists():
        print(f"ERROR: Sites file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return {
        "valid_roles": data.get("valid_roles") or [],
        "valid_os": data.get("valid_os") or [],
        "sites": data.get("sites") or {},
    }


def load_hosts(path: Path = HOSTS_PATH) -> dict:
    """Load and return parsed hosts.yml content.

    Returns a dict where keys are hostnames and values are host attribute dicts.
    Returns an empty dict when the hosts file is an empty template.
    """
    if not path.exists():
        print(f"ERROR: Hosts file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return data.get("hosts") or {}


# ---------------------------------------------------------------------------
# Validate subcommand
# ---------------------------------------------------------------------------


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate inventory files for structural correctness.

    Checks:
        - All host 'site' references exist in sites.yml
        - All host roles are listed in valid_roles
        - All host os values are listed in valid_os
        - No duplicate hostnames (enforced by YAML key uniqueness, but we
          warn if the hosts map is unexpectedly empty)
        - Required fields are present on every host entry
    """
    site_data = load_sites()
    hosts = load_hosts()

    valid_roles = set(site_data["valid_roles"])
    valid_os = set(site_data["valid_os"])
    valid_sites = set(site_data["sites"].keys())

    errors: list[str] = []
    warnings: list[str] = []

    if not valid_roles:
        warnings.append("No valid_roles defined in sites.yml -- role checks skipped")
    if not valid_os:
        warnings.append("No valid_os defined in sites.yml -- OS checks skipped")
    if not valid_sites:
        warnings.append("No sites defined in sites.yml")
    if not hosts:
        warnings.append("No hosts defined in hosts.yml")

    for hostname, attrs in hosts.items():
        prefix = f"Host '{hostname}'"

        if not isinstance(attrs, dict):
            errors.append(f"{prefix}: entry must be a mapping, got {type(attrs).__name__}")
            continue

        # -- Required field: site
        host_site = attrs.get("site")
        if not host_site:
            errors.append(f"{prefix}: missing required field 'site'")
        elif valid_sites and host_site not in valid_sites:
            errors.append(f"{prefix}: site '{host_site}' not defined in sites.yml")

        # -- Required field: roles
        host_roles = attrs.get("roles")
        if not host_roles:
            errors.append(f"{prefix}: missing required field 'roles'")
        elif not isinstance(host_roles, list):
            errors.append(f"{prefix}: 'roles' must be a list")
        elif valid_roles:
            for role in host_roles:
                if role not in valid_roles:
                    errors.append(f"{prefix}: invalid role '{role}' (valid: {', '.join(sorted(valid_roles))})")

        # -- Required field: os
        host_os = attrs.get("os")
        if not host_os:
            errors.append(f"{prefix}: missing required field 'os'")
        elif valid_os and host_os not in valid_os:
            errors.append(f"{prefix}: invalid os '{host_os}' (valid: {', '.join(sorted(valid_os))})")

        # -- Optional but recommended: ip
        if not attrs.get("ip"):
            warnings.append(f"{prefix}: no 'ip' specified (required for Ansible deployment)")

    # -- Print results
    for warning in warnings:
        print(f"  WARN  {warning}")
    for error in errors:
        print(f"  ERROR {error}")

    total_hosts = len(hosts)
    total_sites = len(valid_sites)

    if errors:
        print(f"\nValidation FAILED: {len(errors)} error(s) across {total_hosts} host(s) in {total_sites} site(s)")
        return 1

    print(f"\nValidation PASSED: {total_hosts} host(s) across {total_sites} site(s), 0 errors")
    return 0


# ---------------------------------------------------------------------------
# Report subcommand
# ---------------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> int:
    """Print a summary report of the fleet inventory.

    Breaks down host counts by site, by role, and by OS. Useful for auditing
    fleet coverage before or after deployment changes.
    """
    site_data = load_sites()
    hosts = load_hosts()

    if not hosts:
        print("No hosts defined in hosts.yml. Nothing to report.")
        return 0

    site_counter: Counter = Counter()
    role_counter: Counter = Counter()
    os_counter: Counter = Counter()

    for hostname, attrs in hosts.items():
        if not isinstance(attrs, dict):
            continue
        site_counter[attrs.get("site", "<unset>")] += 1
        os_counter[attrs.get("os", "<unset>")] += 1
        for role in (attrs.get("roles") or []):
            role_counter[role] += 1

    # -- Fleet summary header
    print("=" * 60)
    print(f"  Fleet Inventory Report -- {len(hosts)} host(s)")
    print("=" * 60)

    # -- By site
    print("\n  Hosts by Site:")
    print("  " + "-" * 40)
    for site, count in site_counter.most_common():
        site_display = site
        site_meta = site_data["sites"].get(site, {})
        if isinstance(site_meta, dict) and site_meta.get("display_name"):
            site_display = f"{site} ({site_meta['display_name']})"
        print(f"    {site_display:<35} {count:>4}")

    # -- By role
    print("\n  Hosts by Role (a host may have multiple roles):")
    print("  " + "-" * 40)
    for role, count in role_counter.most_common():
        print(f"    {role:<35} {count:>4}")

    # -- By OS
    print("\n  Hosts by OS:")
    print("  " + "-" * 40)
    for os_type, count in os_counter.most_common():
        print(f"    {os_type:<35} {count:>4}")

    print()
    return 0


# ---------------------------------------------------------------------------
# Import subcommand
# ---------------------------------------------------------------------------


def cmd_import(args: argparse.Namespace) -> int:
    """Import hosts from a CSV file and merge into hosts.yml.

    Expected CSV columns: hostname, site, roles, os, ip, notes
    The 'roles' column accepts semicolon-delimited values for multi-role hosts
    (e.g., "dc;dns"). Single roles are also accepted without a delimiter.

    Existing hosts in hosts.yml are preserved; new entries are appended.
    Duplicate hostnames (already present in hosts.yml) are skipped with a warning.
    """
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    # Load existing inventory for duplicate detection
    existing_hosts = load_hosts()

    new_hosts: dict = {}
    skipped = 0

    with open(csv_path, "r", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)

        # Validate expected columns
        required_columns = {"hostname", "site", "roles", "os"}
        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            print(f"ERROR: CSV missing required columns: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

        for row_num, row in enumerate(reader, start=2):
            hostname = (row.get("hostname") or "").strip()
            if not hostname:
                print(f"  WARN  Row {row_num}: empty hostname, skipping")
                continue

            if hostname in existing_hosts:
                print(f"  WARN  Row {row_num}: '{hostname}' already in hosts.yml, skipping")
                skipped += 1
                continue

            if hostname in new_hosts:
                print(f"  WARN  Row {row_num}: duplicate '{hostname}' in CSV, skipping")
                skipped += 1
                continue

            # Parse roles: support semicolon or comma delimiters
            roles_raw = (row.get("roles") or "").strip()
            roles = [r.strip() for r in roles_raw.replace(",", ";").split(";") if r.strip()]

            new_hosts[hostname] = {
                "site": (row.get("site") or "").strip(),
                "roles": roles,
                "os": (row.get("os") or "").strip(),
                "ip": (row.get("ip") or "").strip() or None,
                "notes": (row.get("notes") or "").strip() or None,
            }

    if not new_hosts:
        print("No new hosts to import.")
        return 0

    # Merge and write back
    merged = dict(existing_hosts)
    merged.update(new_hosts)

    output = {"hosts": merged}

    # Write with a header comment preserved
    header = (
        "# Host Inventory -- Server and Device Registry\n"
        "# Auto-generated entries below. See inventory/hosts.csv.example for CSV format.\n"
        "#\n"
        "# Validate after import:\n"
        "#   python3 scripts/fleet_inventory.py validate\n\n"
    )

    with open(HOSTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.dump(output, fh, default_flow_style=False, sort_keys=False)

    print(f"Imported {len(new_hosts)} host(s), skipped {skipped}. Total: {len(merged)} host(s).")
    print(f"Written to: {HOSTS_PATH}")
    print("\nRun validation to confirm correctness:")
    print(f"  python3 scripts/fleet_inventory.py validate")
    return 0


# ---------------------------------------------------------------------------
# Ansible inventory generation subcommand
# ---------------------------------------------------------------------------


def cmd_ansible_inventory(args: argparse.Namespace) -> int:
    """Generate Ansible inventory YAML grouped by site, role, and OS.

    Outputs to stdout so it can be redirected to a file:
        python3 scripts/fleet_inventory.py ansible-inventory > ansible/inventory.yml
    """
    site_data = load_sites()
    hosts = load_hosts()

    # Build group membership maps
    os_groups: dict[str, dict] = {}
    site_groups: dict[str, dict] = {}
    role_groups: dict[str, dict] = {}

    for hostname, attrs in hosts.items():
        if not isinstance(attrs, dict):
            continue

        host_ip = attrs.get("ip")
        host_entry = {"ansible_host": host_ip} if host_ip else {}

        # OS group
        host_os = attrs.get("os", "unknown")
        os_groups.setdefault(host_os, {})
        os_groups[host_os][hostname] = host_entry

        # Site group (normalize hyphens to underscores for Ansible compatibility)
        host_site = (attrs.get("site") or "unknown").replace("-", "_")
        site_groups.setdefault(host_site, {})
        site_groups[host_site][hostname] = host_entry

        # Role groups
        for role in (attrs.get("roles") or []):
            role_key = f"role_{role}"
            role_groups.setdefault(role_key, {})
            role_groups[role_key][hostname] = host_entry

    # Assemble the inventory structure
    children: dict = {}

    for os_name, members in sorted(os_groups.items()):
        children[os_name] = {"hosts": members}

    for site_name, members in sorted(site_groups.items()):
        children[site_name] = {"hosts": members}

    for role_name, members in sorted(role_groups.items()):
        children[role_name] = {"hosts": members}

    inventory = {"all": {"children": children}}

    header = (
        "# Ansible Inventory -- Generated from inventory/hosts.yml\n"
        "# Regenerate with:\n"
        "#   python3 scripts/fleet_inventory.py ansible-inventory > ansible/inventory.yml\n"
    )

    print(header)
    print(yaml.dump(inventory, default_flow_style=False, sort_keys=False), end="")
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        description="Fleet inventory management for the monitoring stack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/fleet_inventory.py validate\n"
            "  python3 scripts/fleet_inventory.py report\n"
            "  python3 scripts/fleet_inventory.py import --csv hosts.csv\n"
            "  python3 scripts/fleet_inventory.py ansible-inventory > ansible/inventory.yml\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    subparsers.add_parser("validate", help="Validate sites.yml and hosts.yml")

    # report
    subparsers.add_parser("report", help="Print fleet summary report")

    # import
    import_parser = subparsers.add_parser("import", help="Import hosts from CSV")
    import_parser.add_argument(
        "--csv",
        required=True,
        help="Path to CSV file with columns: hostname, site, roles, os, ip, notes",
    )

    # ansible-inventory
    subparsers.add_parser(
        "ansible-inventory",
        help="Generate Ansible inventory YAML to stdout",
    )

    args = parser.parse_args()

    dispatch = {
        "validate": cmd_validate,
        "report": cmd_report,
        "import": cmd_import,
        "ansible-inventory": cmd_ansible_inventory,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
