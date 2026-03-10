#!/usr/bin/env python3
"""
Grafana RBAC Validation Tool

Queries a running Grafana instance and compares its current teams, folders,
and folder permissions against the desired state defined in
folder-permissions.yml. Reports any discrepancies.

Designed for use in CI pipelines: returns exit code 1 when discrepancies
are found, 0 when the actual state matches the desired state.

Checks performed:
  - Teams referenced in config exist in Grafana
  - Folders referenced in config exist in Grafana
  - Folder permissions match config (correct teams, correct permission levels)
  - Extra permissions not defined in config are flagged

Exit codes:
    0 -- No discrepancies found
    1 -- One or more discrepancies found, or an error occurred

Usage:
    python scripts/validate_rbac.py --grafana-url http://localhost:3000 --api-key <token>
    python scripts/validate_rbac.py --grafana-url http://localhost:3000 --user admin --password admin
"""

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

DEFAULT_CONFIG_PATH = Path("configs/grafana/provisioning/access-control/folder-permissions.yml")

PERMISSION_LABELS = {1: "View", 2: "Edit", 4: "Admin"}


# ---------------------------------------------------------------------------
# Grafana API client (minimal, same pattern as configure_rbac.py)
# ---------------------------------------------------------------------------

class GrafanaClient:
    """Minimal Grafana HTTP client using only stdlib."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        user: str | None = None,
        password: str | None = None,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user = user
        self.password = password

        self._ssl_context: ssl.SSLContext | None = None
        if not verify_ssl:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

    def get(self, path: str) -> dict | list | None:
        """Execute a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, method="GET")
        request.add_header("Accept", "application/json")

        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        elif self.user and self.password:
            import base64
            credentials = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            request.add_header("Authorization", f"Basic {credentials}")

        try:
            response = urllib.request.urlopen(request, context=self._ssl_context)
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Grafana API GET {path} returned {exc.code}: {error_body}"
            ) from exc

    def health_check(self) -> bool:
        """Verify connectivity to Grafana."""
        try:
            result = self.get("/api/health")
            return isinstance(result, dict) and result.get("database") == "ok"
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    """Load the folder-permissions YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "folders" not in data:
        raise ValueError("Config must contain a top-level 'folders' key")

    return data


def collect_required_teams(config: dict) -> set[str]:
    """Extract every team name referenced in the config."""
    teams: set[str] = set()
    for folder in config.get("folders", []):
        for perm in folder.get("permissions", []):
            team_name = perm.get("team")
            if team_name:
                teams.add(team_name)
    return teams


# ---------------------------------------------------------------------------
# Discrepancy detection
# ---------------------------------------------------------------------------

class Discrepancy:
    """A single mismatch between desired and actual RBAC state."""

    def __init__(self, category: str, resource: str, detail: str):
        self.category = category
        self.resource = resource
        self.detail = detail

    def __str__(self) -> str:
        return f"[{self.category}] {self.resource}: {self.detail}"


def check_teams(
    client: GrafanaClient,
    required_teams: set[str],
) -> tuple[list[Discrepancy], dict[str, int]]:
    """Verify all required teams exist. Return discrepancies and team id map."""
    discrepancies: list[Discrepancy] = []

    teams_response = client.get("/api/teams/search?perpage=1000") or {}
    existing_teams = teams_response.get("teams", [])

    team_map: dict[str, int] = {}
    for team in existing_teams:
        team_map[team["name"]] = team["id"]

    for team_name in sorted(required_teams):
        if team_name not in team_map:
            discrepancies.append(Discrepancy(
                "MISSING_TEAM",
                team_name,
                "Team defined in config but does not exist in Grafana",
            ))

    return discrepancies, team_map


def check_folders_and_permissions(
    client: GrafanaClient,
    config: dict,
    team_map: dict[str, int],
) -> list[Discrepancy]:
    """Verify folders exist and permissions match the desired state."""
    discrepancies: list[Discrepancy] = []

    # Build a set of existing folder UIDs
    existing_folders = client.get("/api/folders?limit=1000") or []
    existing_uids: set[str] = set()
    for folder in existing_folders:
        if isinstance(folder, dict) and "uid" in folder:
            existing_uids.add(folder["uid"])

    # Reverse lookup: team id -> name
    id_to_name: dict[int, str] = {tid: name for name, tid in team_map.items()}

    for folder_def in config.get("folders", []):
        uid = folder_def["uid"]
        title = folder_def.get("title", uid)

        if uid not in existing_uids:
            discrepancies.append(Discrepancy(
                "MISSING_FOLDER",
                title,
                f"Folder uid='{uid}' defined in config but does not exist in Grafana",
            ))
            continue

        # Fetch actual permissions for this folder
        try:
            actual_perms = client.get(f"/api/folders/{uid}/permissions") or []
        except RuntimeError as exc:
            discrepancies.append(Discrepancy(
                "API_ERROR",
                title,
                f"Could not read permissions: {exc}",
            ))
            continue

        # Build lookup of actual team permissions: team_id -> permission_level
        actual_team_perms: dict[int, int] = {}
        for perm in actual_perms:
            team_id = perm.get("teamId", 0)
            if team_id:
                actual_team_perms[team_id] = perm.get("permission", 0)

        # Check each desired permission
        desired_team_ids: set[int] = set()
        for perm_def in folder_def.get("permissions", []):
            team_name = perm_def["team"]
            desired_level = perm_def["permission"]
            team_id = team_map.get(team_name)

            if team_id is None:
                # Already reported as MISSING_TEAM
                continue

            desired_team_ids.add(team_id)
            actual_level = actual_team_perms.get(team_id)

            if actual_level is None:
                discrepancies.append(Discrepancy(
                    "MISSING_PERMISSION",
                    title,
                    f"Team '{team_name}' should have "
                    f"{PERMISSION_LABELS.get(desired_level, str(desired_level))} "
                    f"but has no permission assigned",
                ))
            elif actual_level != desired_level:
                discrepancies.append(Discrepancy(
                    "WRONG_PERMISSION",
                    title,
                    f"Team '{team_name}' has "
                    f"{PERMISSION_LABELS.get(actual_level, str(actual_level))} "
                    f"but should have "
                    f"{PERMISSION_LABELS.get(desired_level, str(desired_level))}",
                ))

        # Check for extra team permissions not in config
        for team_id, actual_level in actual_team_perms.items():
            if team_id not in desired_team_ids:
                team_name = id_to_name.get(team_id, f"team-id-{team_id}")
                discrepancies.append(Discrepancy(
                    "EXTRA_PERMISSION",
                    title,
                    f"Team '{team_name}' has "
                    f"{PERMISSION_LABELS.get(actual_level, str(actual_level))} "
                    f"but is not defined in config",
                ))

    return discrepancies


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Grafana RBAC state against folder-permissions.yml"
    )
    parser.add_argument(
        "--grafana-url",
        default="http://localhost:3000",
        help="Grafana base URL (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--api-key",
        help="Grafana API key or service account token",
    )
    parser.add_argument(
        "--user",
        help="Grafana admin username (basic auth)",
    )
    parser.add_argument(
        "--password",
        help="Grafana admin password (basic auth)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to folder-permissions.yml (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS certificate verification",
    )
    args = parser.parse_args()

    # Load and validate config
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    required_teams = collect_required_teams(config)

    # Connect to Grafana
    client = GrafanaClient(
        base_url=args.grafana_url,
        api_key=args.api_key,
        user=args.user,
        password=args.password,
        verify_ssl=not args.insecure,
    )

    if not client.health_check():
        print(f"ERROR: Cannot connect to Grafana at {args.grafana_url}", file=sys.stderr)
        return 1

    print(f"Connected to Grafana at {args.grafana_url}")
    print(f"Config: {args.config}")
    print(f"Required teams: {len(required_teams)}")
    print(f"Defined folders: {len(config.get('folders', []))}")
    print()

    # Run checks
    all_discrepancies: list[Discrepancy] = []

    print("Checking teams...")
    team_discrepancies, team_map = check_teams(client, required_teams)
    all_discrepancies.extend(team_discrepancies)

    print("Checking folders and permissions...")
    folder_discrepancies = check_folders_and_permissions(client, config, team_map)
    all_discrepancies.extend(folder_discrepancies)

    # Report
    print()
    if not all_discrepancies:
        print("PASSED -- No discrepancies found. RBAC state matches config.")
        return 0

    print(f"FAILED -- {len(all_discrepancies)} discrepancy(ies) found:\n")

    # Group by category for readability
    by_category: dict[str, list[Discrepancy]] = {}
    for disc in all_discrepancies:
        by_category.setdefault(disc.category, []).append(disc)

    for category in sorted(by_category.keys()):
        items = by_category[category]
        print(f"  {category} ({len(items)}):")
        for item in items:
            print(f"    {item.resource}: {item.detail}")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
