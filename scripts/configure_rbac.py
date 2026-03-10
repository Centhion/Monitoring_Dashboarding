#!/usr/bin/env python3
"""
Grafana RBAC Configuration Tool

Reads the folder-permissions.yml reference file and applies the defined
permission model to a running Grafana instance via its HTTP API. Creates
teams, folders, and folder-level permissions as needed.

Subcommands:
    apply    -- Apply the full permission model (teams, folders, permissions)
    validate -- Parse and validate the YAML config without contacting Grafana
    report   -- Query a running Grafana instance and display current RBAC state

Authentication:
    Provide either --api-key (service account token) or --user/--password
    (basic auth). The authenticated identity must have Grafana Admin privileges.

Exit codes:
    0 -- Success
    1 -- Failure (API error, config error, or validation failure)

Usage:
    python scripts/configure_rbac.py apply --grafana-url http://localhost:3000 --api-key <token>
    python scripts/configure_rbac.py apply --dry-run --grafana-url http://localhost:3000 --api-key <token>
    python scripts/configure_rbac.py validate
    python scripts/configure_rbac.py report --grafana-url http://localhost:3000 --api-key <token>
"""

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

# pyyaml is the single external dependency
try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

# Default path to the folder-permissions reference file
DEFAULT_CONFIG_PATH = Path("configs/grafana/provisioning/access-control/folder-permissions.yml")

# Grafana numeric permission levels
PERMISSION_LABELS = {1: "View", 2: "Edit", 4: "Admin"}


# ---------------------------------------------------------------------------
# Grafana API client
# ---------------------------------------------------------------------------

class GrafanaClient:
    """Lightweight HTTP client for the Grafana REST API.

    Uses only stdlib urllib so there are no additional dependencies beyond
    PyYAML. Supports API-key (Bearer token) and basic authentication.
    """

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

        # Build a default SSL context; disable verification only when asked
        self._ssl_context: ssl.SSLContext | None = None
        if not verify_ssl:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

    def _build_request(self, method: str, path: str, body: dict | None = None) -> urllib.request.Request:
        """Construct an authenticated urllib Request."""
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None

        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")

        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        elif self.user and self.password:
            import base64
            credentials = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            request.add_header("Authorization", f"Basic {credentials}")

        return request

    def _do(self, method: str, path: str, body: dict | None = None) -> dict | list | None:
        """Execute an HTTP request and return parsed JSON response."""
        request = self._build_request(method, path, body)
        try:
            response = urllib.request.urlopen(request, context=self._ssl_context)
            response_body = response.read().decode("utf-8")
            if response_body:
                return json.loads(response_body)
            return None
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Grafana API {method} {path} returned {exc.code}: {error_body}"
            ) from exc

    def get(self, path: str) -> dict | list | None:
        return self._do("GET", path)

    def post(self, path: str, body: dict | None = None) -> dict | list | None:
        return self._do("POST", path, body)

    def health_check(self) -> bool:
        """Verify connectivity to Grafana."""
        try:
            result = self.get("/api/health")
            return isinstance(result, dict) and result.get("database") == "ok"
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Configuration loading and validation
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    """Load and return the folder-permissions YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping, got {type(data).__name__}")

    return data


def validate_config(config: dict) -> list[str]:
    """Validate the structure of folder-permissions config.

    Returns a list of error messages. An empty list means the config is valid.
    """
    errors: list[str] = []

    folders = config.get("folders")
    if folders is None:
        errors.append("Missing top-level 'folders' key")
        return errors

    if not isinstance(folders, list):
        errors.append(f"'folders' must be a list, got {type(folders).__name__}")
        return errors

    seen_uids: set[str] = set()

    for idx, folder in enumerate(folders):
        prefix = f"folders[{idx}]"

        if not isinstance(folder, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue

        uid = folder.get("uid")
        if not uid or not isinstance(uid, str):
            errors.append(f"{prefix}: missing or invalid 'uid'")
        elif uid in seen_uids:
            errors.append(f"{prefix}: duplicate uid '{uid}'")
        else:
            seen_uids.add(uid)

        title = folder.get("title")
        if not title or not isinstance(title, str):
            errors.append(f"{prefix}: missing or invalid 'title'")

        permissions = folder.get("permissions")
        if permissions is None:
            errors.append(f"{prefix}: missing 'permissions'")
            continue

        if not isinstance(permissions, list):
            errors.append(f"{prefix}: 'permissions' must be a list")
            continue

        for p_idx, perm in enumerate(permissions):
            p_prefix = f"{prefix}.permissions[{p_idx}]"
            if not isinstance(perm, dict):
                errors.append(f"{p_prefix}: must be a mapping")
                continue

            if "team" not in perm:
                errors.append(f"{p_prefix}: missing 'team'")

            perm_level = perm.get("permission")
            if perm_level not in PERMISSION_LABELS:
                errors.append(
                    f"{p_prefix}: invalid permission level {perm_level} "
                    f"(valid: {list(PERMISSION_LABELS.keys())})"
                )

    return errors


def collect_required_teams(config: dict) -> set[str]:
    """Extract the set of all team names referenced in the config."""
    teams: set[str] = set()
    for folder in config.get("folders", []):
        for perm in folder.get("permissions", []):
            team_name = perm.get("team")
            if team_name:
                teams.add(team_name)
    return teams


# ---------------------------------------------------------------------------
# Apply subcommand
# ---------------------------------------------------------------------------

def ensure_teams(client: GrafanaClient, required_teams: set[str], dry_run: bool) -> dict[str, int]:
    """Create any missing teams and return a name-to-id mapping."""
    existing = client.get("/api/teams/search?perpage=1000") or {}
    team_map: dict[str, int] = {}

    for team in existing.get("teams", []):
        team_map[team["name"]] = team["id"]

    for team_name in sorted(required_teams):
        if team_name in team_map:
            print(f"  Team '{team_name}' exists (id={team_map[team_name]})")
        elif dry_run:
            print(f"  Team '{team_name}' WOULD BE CREATED (dry-run)")
        else:
            result = client.post("/api/teams", {"name": team_name})
            team_id = result.get("teamId") if isinstance(result, dict) else None
            if team_id:
                team_map[team_name] = team_id
                print(f"  Team '{team_name}' created (id={team_id})")
            else:
                print(f"  WARNING: Failed to create team '{team_name}': {result}")

    return team_map


def ensure_folders(client: GrafanaClient, config: dict, dry_run: bool) -> dict[str, str]:
    """Create any missing folders and return a uid-to-uid mapping (identity for existing)."""
    existing_folders = client.get("/api/folders?limit=1000") or []
    existing_uids: set[str] = {f["uid"] for f in existing_folders if isinstance(f, dict)}
    folder_uid_map: dict[str, str] = {}

    for folder_def in config.get("folders", []):
        uid = folder_def["uid"]
        title = folder_def["title"]
        folder_uid_map[uid] = uid

        if uid in existing_uids:
            print(f"  Folder '{title}' (uid={uid}) exists")
        elif dry_run:
            print(f"  Folder '{title}' (uid={uid}) WOULD BE CREATED (dry-run)")
        else:
            try:
                client.post("/api/folders", {"uid": uid, "title": title})
                print(f"  Folder '{title}' (uid={uid}) created")
            except RuntimeError as exc:
                print(f"  WARNING: Failed to create folder '{title}': {exc}")

    return folder_uid_map


def apply_folder_permissions(
    client: GrafanaClient,
    config: dict,
    team_map: dict[str, int],
    dry_run: bool,
) -> None:
    """Set folder permissions according to the config."""
    for folder_def in config.get("folders", []):
        uid = folder_def["uid"]
        title = folder_def["title"]

        items: list[dict] = []
        for perm in folder_def.get("permissions", []):
            team_name = perm["team"]
            team_id = team_map.get(team_name)
            if team_id is None:
                print(f"  WARNING: Team '{team_name}' not found, skipping permission for folder '{title}'")
                continue
            items.append({
                "teamId": team_id,
                "permission": perm["permission"],
            })

        if not items:
            print(f"  Folder '{title}': no valid permissions to apply")
            continue

        if dry_run:
            print(f"  Folder '{title}': WOULD SET {len(items)} permission(s) (dry-run)")
            for item in items:
                team_name = _team_name_by_id(team_map, item["teamId"])
                level = PERMISSION_LABELS.get(item["permission"], str(item["permission"]))
                print(f"    {team_name} -> {level}")
        else:
            try:
                client.post(f"/api/folders/{uid}/permissions", {"items": items})
                print(f"  Folder '{title}': applied {len(items)} permission(s)")
            except RuntimeError as exc:
                print(f"  ERROR: Failed to set permissions on folder '{title}': {exc}")


def _team_name_by_id(team_map: dict[str, int], team_id: int) -> str:
    """Reverse-lookup a team name from the id mapping."""
    for name, tid in team_map.items():
        if tid == team_id:
            return name
    return f"team-id-{team_id}"


def cmd_apply(args: argparse.Namespace) -> int:
    """Apply the RBAC model to a running Grafana instance."""
    config = load_config(args.config)

    # Validate first
    errors = validate_config(config)
    if errors:
        print("Configuration errors:")
        for err in errors:
            print(f"  {err}")
        return 1

    client = GrafanaClient(
        base_url=args.grafana_url,
        api_key=args.api_key,
        user=args.user,
        password=args.password,
        verify_ssl=not args.insecure,
    )

    if not client.health_check():
        print(f"ERROR: Cannot connect to Grafana at {args.grafana_url}")
        return 1

    required_teams = collect_required_teams(config)

    if args.dry_run:
        print("[DRY RUN] No changes will be applied.\n")

    print("--- Teams ---")
    team_map = ensure_teams(client, required_teams, args.dry_run)

    print("\n--- Folders ---")
    ensure_folders(client, config, args.dry_run)

    print("\n--- Folder Permissions ---")
    apply_folder_permissions(client, config, team_map, args.dry_run)

    print("\nDone.")
    return 0


# ---------------------------------------------------------------------------
# Validate subcommand
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> int:
    """Parse and validate the config file without contacting Grafana."""
    config = load_config(args.config)
    errors = validate_config(config)

    if errors:
        print(f"Validation FAILED ({len(errors)} error(s)):")
        for err in errors:
            print(f"  {err}")
        return 1

    folders = config.get("folders", [])
    teams = collect_required_teams(config)

    print("Validation PASSED")
    print(f"  Folders defined: {len(folders)}")
    print(f"  Teams referenced: {len(teams)}")
    for team in sorted(teams):
        print(f"    - {team}")

    total_perms = sum(
        len(f.get("permissions", [])) for f in folders
    )
    print(f"  Total permission entries: {total_perms}")

    return 0


# ---------------------------------------------------------------------------
# Report subcommand
# ---------------------------------------------------------------------------

def cmd_report(args: argparse.Namespace) -> int:
    """Query Grafana and display current RBAC state."""
    client = GrafanaClient(
        base_url=args.grafana_url,
        api_key=args.api_key,
        user=args.user,
        password=args.password,
        verify_ssl=not args.insecure,
    )

    if not client.health_check():
        print(f"ERROR: Cannot connect to Grafana at {args.grafana_url}")
        return 1

    # Teams
    print("--- Teams ---")
    teams_response = client.get("/api/teams/search?perpage=1000") or {}
    teams = teams_response.get("teams", [])
    if not teams:
        print("  No teams found.")
    for team in teams:
        member_count = team.get("memberCount", 0)
        print(f"  {team['name']} (id={team['id']}, members={member_count})")

    # Build team id-to-name lookup for permission display
    team_id_to_name: dict[int, str] = {t["id"]: t["name"] for t in teams}

    # Folders and their permissions
    print("\n--- Folders ---")
    folders = client.get("/api/folders?limit=1000") or []
    if not folders:
        print("  No folders found.")

    for folder in folders:
        uid = folder.get("uid", "unknown")
        title = folder.get("title", "untitled")
        print(f"\n  {title} (uid={uid})")

        try:
            perms = client.get(f"/api/folders/{uid}/permissions") or []
        except RuntimeError:
            print("    (unable to read permissions)")
            continue

        if not perms:
            print("    No explicit permissions set.")
            continue

        for perm in perms:
            team_id = perm.get("teamId", 0)
            user_id = perm.get("userId", 0)
            role = perm.get("role", "")
            level = PERMISSION_LABELS.get(perm.get("permission", 0), "Unknown")

            if team_id:
                name = team_id_to_name.get(team_id, f"team-id-{team_id}")
                print(f"    Team '{name}' -> {level}")
            elif user_id:
                print(f"    User id={user_id} -> {level}")
            elif role:
                print(f"    Role '{role}' -> {level}")

    print()
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Configure Grafana RBAC from folder-permissions.yml"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared arguments for commands that talk to Grafana
    grafana_args = argparse.ArgumentParser(add_help=False)
    grafana_args.add_argument(
        "--grafana-url",
        default="http://localhost:3000",
        help="Grafana base URL (default: http://localhost:3000)",
    )
    grafana_args.add_argument(
        "--api-key",
        help="Grafana API key or service account token",
    )
    grafana_args.add_argument(
        "--user",
        help="Grafana admin username (basic auth)",
    )
    grafana_args.add_argument(
        "--password",
        help="Grafana admin password (basic auth)",
    )
    grafana_args.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS certificate verification",
    )

    # Config path argument shared by apply and validate
    config_args = argparse.ArgumentParser(add_help=False)
    config_args.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to folder-permissions.yml (default: {DEFAULT_CONFIG_PATH})",
    )

    # apply
    apply_parser = subparsers.add_parser(
        "apply",
        parents=[grafana_args, config_args],
        help="Apply RBAC configuration to Grafana",
    )
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without applying",
    )

    # validate
    subparsers.add_parser(
        "validate",
        parents=[config_args],
        help="Validate config file syntax and structure",
    )

    # report
    subparsers.add_parser(
        "report",
        parents=[grafana_args],
        help="Display current RBAC state from a running Grafana instance",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "apply":
            return cmd_apply(args)
        elif args.command == "validate":
            return cmd_validate(args)
        elif args.command == "report":
            return cmd_report(args)
        else:
            parser.print_help()
            return 1
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
