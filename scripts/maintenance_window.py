#!/usr/bin/env python3
"""
Maintenance Window Management Script (Phase 9E)

Creates and removes Grafana mute timings programmatically for planned
maintenance windows. Use this to silence alerts during patching, upgrades,
or other expected downtime without editing YAML config files.

Usage:
    # Create a 4-hour maintenance window starting now
    python3 scripts/maintenance_window.py create \
        --name "Patching site-a" \
        --duration 4h \
        --grafana-url http://localhost:3000 \
        --api-key "$GRAFANA_API_KEY"

    # Create a maintenance window for a specific time range
    python3 scripts/maintenance_window.py create \
        --name "SQL upgrade" \
        --start "2026-03-15T02:00:00Z" \
        --end "2026-03-15T06:00:00Z" \
        --grafana-url http://localhost:3000 \
        --api-key "$GRAFANA_API_KEY"

    # List active maintenance windows
    python3 scripts/maintenance_window.py list \
        --grafana-url http://localhost:3000 \
        --api-key "$GRAFANA_API_KEY"

    # Remove a maintenance window by name
    python3 scripts/maintenance_window.py delete \
        --name "Patching site-a" \
        --grafana-url http://localhost:3000 \
        --api-key "$GRAFANA_API_KEY"

Environment Variables:
    GRAFANA_URL      -- Grafana base URL (default: http://localhost:3000)
    GRAFANA_API_KEY  -- Grafana API key with alerting permissions
    GRAFANA_USER     -- Grafana username (alternative to API key)
    GRAFANA_PASSWORD -- Grafana password (alternative to API key)

Requirements:
    - Grafana 9.0+ (mute timings API)
    - API key with "Admin" or "Editor" role
    - Python 3.10+ (no external dependencies)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


def parse_duration(duration_str: str) -> timedelta:
    """Parse a human-readable duration string into a timedelta.

    Supports formats like '4h', '30m', '2h30m', '1d', '1d4h'.
    """
    total_minutes = 0
    current_num = ""

    for char in duration_str:
        if char.isdigit():
            current_num += char
        elif char == "d":
            total_minutes += int(current_num) * 24 * 60
            current_num = ""
        elif char == "h":
            total_minutes += int(current_num) * 60
            current_num = ""
        elif char == "m":
            total_minutes += int(current_num)
            current_num = ""
        else:
            print(f"Error: invalid duration character '{char}' in '{duration_str}'")
            sys.exit(1)

    if current_num:
        # Bare number without unit defaults to minutes
        total_minutes += int(current_num)

    if total_minutes <= 0:
        print(f"Error: duration must be positive, got '{duration_str}'")
        sys.exit(1)

    return timedelta(minutes=total_minutes)


def grafana_request(
    grafana_url: str,
    path: str,
    method: str = "GET",
    data: dict | None = None,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict | list | None:
    """Make an authenticated request to the Grafana API."""
    url = f"{grafana_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif username and password:
        import base64

        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    else:
        print("Error: provide --api-key or GRAFANA_USER + GRAFANA_PASSWORD")
        sys.exit(1)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 204:
                return None
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else ""
        print(f"Error: Grafana API returned {exc.code}: {error_body}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Error: cannot reach Grafana at {grafana_url}: {exc.reason}")
        sys.exit(1)


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new mute timing (maintenance window)."""
    now = datetime.now(timezone.utc)

    if args.start:
        start_time = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
    else:
        start_time = now

    if args.end:
        end_time = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
    elif args.duration:
        end_time = start_time + parse_duration(args.duration)
    else:
        print("Error: provide --end or --duration")
        sys.exit(1)

    # Grafana mute timings use time_intervals with specific time/day formats.
    # For ad-hoc windows, we create a mute timing that matches the exact
    # date range. This is less elegant than Alertmanager silences but works
    # with Grafana's provisioning model.
    mute_timing = {
        "name": args.name,
        "time_intervals": [
            {
                "times": [
                    {
                        "start_time": start_time.strftime("%H:%M"),
                        "end_time": end_time.strftime("%H:%M"),
                    }
                ],
                "months": [str(start_time.month)],
                "days_of_month": [str(start_time.day)],
            }
        ],
    }

    result = grafana_request(
        args.grafana_url,
        "/api/v1/provisioning/mute-timings",
        method="POST",
        data=mute_timing,
        api_key=args.api_key,
        username=args.username,
        password=args.password,
    )

    print(f"Created maintenance window: {args.name}")
    print(f"  Start: {start_time.isoformat()}")
    print(f"  End:   {end_time.isoformat()}")
    print(f"  Duration: {end_time - start_time}")
    if result:
        print(f"  Grafana response: {json.dumps(result, indent=2)}")

    print()
    print("NOTE: To activate this mute timing, add it to a notification policy")
    print("route via the Grafana UI or API. The mute timing exists but does not")
    print("suppress alerts until it is referenced by a notification policy.")


def cmd_list(args: argparse.Namespace) -> None:
    """List all mute timings."""
    result = grafana_request(
        args.grafana_url,
        "/api/v1/provisioning/mute-timings",
        api_key=args.api_key,
        username=args.username,
        password=args.password,
    )

    if not result:
        print("No mute timings configured.")
        return

    print(f"{'Name':<30} {'Intervals'}")
    print("-" * 70)
    for timing in result:
        name = timing.get("name", "unnamed")
        intervals = timing.get("time_intervals", [])
        interval_str = "; ".join(
            f"{i.get('times', [{}])[0].get('start_time', '?')}-"
            f"{i.get('times', [{}])[0].get('end_time', '?')}"
            for i in intervals
        )
        print(f"{name:<30} {interval_str}")


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a mute timing by name."""
    grafana_request(
        args.grafana_url,
        f"/api/v1/provisioning/mute-timings/{args.name}",
        method="DELETE",
        api_key=args.api_key,
        username=args.username,
        password=args.password,
    )
    print(f"Deleted maintenance window: {args.name}")


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        description="Manage Grafana maintenance windows (mute timings)"
    )
    parser.add_argument(
        "--grafana-url",
        default=os.environ.get("GRAFANA_URL", "http://localhost:3000"),
        help="Grafana base URL (default: $GRAFANA_URL or http://localhost:3000)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GRAFANA_API_KEY"),
        help="Grafana API key (default: $GRAFANA_API_KEY)",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("GRAFANA_USER"),
        help="Grafana username (default: $GRAFANA_USER)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("GRAFANA_PASSWORD"),
        help="Grafana password (default: $GRAFANA_PASSWORD)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # create subcommand
    create_parser = subparsers.add_parser("create", help="Create a maintenance window")
    create_parser.add_argument("--name", required=True, help="Window name")
    create_parser.add_argument("--start", help="Start time (ISO 8601, default: now)")
    create_parser.add_argument("--end", help="End time (ISO 8601)")
    create_parser.add_argument("--duration", help="Duration (e.g., 4h, 30m, 1d)")
    create_parser.set_defaults(func=cmd_create)

    # list subcommand
    list_parser = subparsers.add_parser("list", help="List maintenance windows")
    list_parser.set_defaults(func=cmd_list)

    # delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a maintenance window")
    delete_parser.add_argument("--name", required=True, help="Window name to delete")
    delete_parser.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
