#!/usr/bin/env python3
"""
PoC Environment Setup and Health Checker

One-command startup for the Docker Compose monitoring stack. Validates
prerequisites, starts services, waits for health checks, and verifies
the full stack is operational.

Usage:
    python scripts/stack_manage.py              Start stack and verify health
    python scripts/stack_manage.py --status     Check health of running stack
    python scripts/stack_manage.py --stop       Stop stack (preserve data)
    python scripts/stack_manage.py --reset      Stop stack and delete all data
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_ROOT / "deploy" / "docker" / "docker-compose.yml"
# .env lives at repo root, not beside the compose file
ENV_FILE = PROJECT_ROOT / ".env"

# Service endpoints for health checking
SERVICES = {
    "Prometheus": {
        "url": "http://localhost:9090/-/healthy",
        "ui_url": "http://localhost:9090",
    },
    "Loki": {
        "url": "http://localhost:3100/ready",
        "ui_url": "http://localhost:3100",
    },
    "Alertmanager": {
        "url": "http://localhost:9093/-/healthy",
        "ui_url": "http://localhost:9093",
    },
    "Grafana": {
        "url": "http://localhost:3000/api/health",
        "ui_url": "http://localhost:3000",
    },
}

# Prometheus API endpoints for deeper validation
PROMETHEUS_RULES_URL = "http://localhost:9090/api/v1/rules"
PROMETHEUS_TARGETS_URL = "http://localhost:9090/api/v1/targets"
GRAFANA_DATASOURCES_URL = "http://localhost:3000/api/datasources"


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Execute a shell command and return (exit_code, output)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(cwd) if cwd else None,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except FileNotFoundError:
        return 1, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"


def check_prerequisites() -> bool:
    """Verify Docker and Docker Compose are available."""
    print("Checking prerequisites...")

    # Docker daemon running
    code, output = run_command(["docker", "info"])
    if code != 0:
        print("  ERROR: Docker is not running. Start Docker Desktop first.")
        return False
    print("  Docker: running")

    # Docker Compose available
    code, output = run_command(["docker", "compose", "version"])
    if code != 0:
        print("  ERROR: Docker Compose not available.")
        return False
    version_line = output.strip().split("\n")[0] if output else "unknown"
    print(f"  Compose: {version_line}")

    # .env file exists (optional but recommended)
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print("  .env: found")
    else:
        print("  .env: not found (using defaults -- Teams webhook will be placeholder)")

    return True


def _compose_base_cmd() -> list[str]:
    """Build the base docker compose command with file and env-file flags."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    if ENV_FILE.exists():
        cmd.extend(["--env-file", str(ENV_FILE)])
    return cmd


def start_stack() -> bool:
    """Start the Docker Compose stack."""
    print("\nStarting monitoring stack...")
    cmd = _compose_base_cmd() + ["up", "-d"]
    code, output = run_command(cmd, cwd=PROJECT_ROOT)
    if code != 0:
        print(f"  ERROR: Failed to start stack:\n{output}")
        return False
    print("  Containers starting...")
    return True


def wait_for_health(timeout_seconds: int = 120) -> bool:
    """Wait for all services to pass health checks."""
    print(f"\nWaiting for services to become healthy (timeout: {timeout_seconds}s)...")

    start = time.monotonic()
    healthy = set()

    while time.monotonic() - start < timeout_seconds:
        for name, svc in SERVICES.items():
            if name in healthy:
                continue

            try:
                req = urllib.request.Request(svc["url"], method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        healthy.add(name)
                        elapsed = time.monotonic() - start
                        print(f"  {name}: healthy ({elapsed:.0f}s)")
            except (urllib.error.URLError, OSError):
                pass

        if len(healthy) == len(SERVICES):
            return True

        time.sleep(2)

    # Report which services failed
    unhealthy = set(SERVICES.keys()) - healthy
    for name in unhealthy:
        print(f"  {name}: TIMEOUT -- not healthy after {timeout_seconds}s")

    return False


def validate_prometheus_rules() -> bool:
    """Verify Prometheus loaded recording and alert rules."""
    print("\nValidating Prometheus rules...")
    try:
        req = urllib.request.Request(PROMETHEUS_RULES_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        groups = data.get("data", {}).get("groups", [])
        rule_count = sum(len(g.get("rules", [])) for g in groups)
        group_names = [g["name"] for g in groups]

        print(f"  Rule groups loaded: {len(groups)}")
        for name in group_names:
            print(f"    - {name}")
        print(f"  Total rules: {rule_count}")

        if rule_count == 0:
            print("  WARNING: No rules loaded -- check volume mounts")
            return False

        return True
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"  ERROR: Could not query rules API: {exc}")
        return False


def validate_grafana_datasources() -> bool:
    """Verify Grafana provisioned datasources are accessible."""
    print("\nValidating Grafana datasources...")
    try:
        req = urllib.request.Request(GRAFANA_DATASOURCES_URL, method="GET")
        # Basic auth for Grafana API
        import base64
        credentials = base64.b64encode(b"admin:admin").decode()
        req.add_header("Authorization", f"Basic {credentials}")

        with urllib.request.urlopen(req, timeout=5) as resp:
            datasources = json.loads(resp.read().decode())

        for ds in datasources:
            name = ds.get("name", "unknown")
            ds_type = ds.get("type", "unknown")
            uid = ds.get("uid", "unknown")
            print(f"  {name}: type={ds_type}, uid={uid}")

        expected_uids = {"prometheus", "loki"}
        actual_uids = {ds.get("uid", "") for ds in datasources}
        missing = expected_uids - actual_uids

        if missing:
            print(f"  WARNING: Missing expected datasources: {missing}")
            return False

        print(f"  All {len(expected_uids)} datasources provisioned")
        return True

    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"  ERROR: Could not query Grafana API: {exc}")
        return False


def print_status() -> None:
    """Print current health status of all services."""
    print("\nMonitoring Stack Status")
    print("=" * 50)

    all_healthy = True
    for name, svc in SERVICES.items():
        try:
            req = urllib.request.Request(svc["url"], method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    print(f"  {name:15s}  HEALTHY  {svc['ui_url']}")
                else:
                    print(f"  {name:15s}  UNHEALTHY (HTTP {resp.status})")
                    all_healthy = False
        except (urllib.error.URLError, OSError):
            print(f"  {name:15s}  DOWN")
            all_healthy = False

    print("=" * 50)
    if all_healthy:
        print("  All services healthy")
    else:
        print("  Some services unhealthy -- run: docker compose -f deploy/docker/docker-compose.yml logs")


def stop_stack(remove_volumes: bool = False) -> None:
    """Stop the Docker Compose stack."""
    cmd = _compose_base_cmd() + ["down"]
    if remove_volumes:
        cmd.append("-v")
        print("Stopping stack and removing volumes...")
    else:
        print("Stopping stack (preserving data volumes)...")

    code, output = run_command(cmd, cwd=PROJECT_ROOT)
    if code == 0:
        print("  Stack stopped")
    else:
        print(f"  ERROR: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage the Docker Compose monitoring PoC stack"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Check health of running stack"
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="Stop the stack (preserve data)"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Stop the stack and delete all data volumes"
    )
    parser.add_argument(
        "--demo-data", action="store_true",
        help="After startup, backfill and stream demo data for showcasing dashboards"
    )
    args = parser.parse_args()

    if args.status:
        print_status()
        return 0

    if args.stop:
        stop_stack(remove_volumes=False)
        return 0

    if args.reset:
        stop_stack(remove_volumes=True)
        return 0

    # Full startup flow
    print("=" * 50)
    print("  Monitoring Stack PoC Setup")
    print("=" * 50)

    if not check_prerequisites():
        return 1

    if not start_stack():
        return 1

    if not wait_for_health(timeout_seconds=120):
        print("\nSome services failed to start. Check logs:")
        print("  docker compose -f deploy/docker/docker-compose.yml logs prometheus")
        print("  docker compose -f deploy/docker/docker-compose.yml logs loki")
        print("  docker compose -f deploy/docker/docker-compose.yml logs alertmanager")
        print("  docker compose -f deploy/docker/docker-compose.yml logs grafana")
        return 1

    # Deep validation
    rules_ok = validate_prometheus_rules()
    datasources_ok = validate_grafana_datasources()

    # Summary
    print("\n" + "=" * 50)
    print("  Stack Ready")
    print("=" * 50)
    print(f"  Grafana:      http://localhost:3000  (admin / admin)")
    print(f"  Prometheus:   http://localhost:9090")
    print(f"  Alertmanager: http://localhost:9093")
    print(f"  Loki API:     http://localhost:3100")
    print()

    if rules_ok and datasources_ok:
        print("  All validations passed.")
    else:
        print("  Some validations had warnings -- check output above.")

    # Demo data mode: backfill + continuous push
    if args.demo_data:
        print()
        print("Starting demo data generator...")
        config_path = PROJECT_ROOT / "deploy" / "site_config.yml"
        if not config_path.exists():
            print("  WARNING: deploy/site_config.yml not found.")
            print("  Run deploy_configure.py first to generate site config.")
            print("  Skipping demo data.")
        else:
            try:
                from demo_data_generator import build_inventory, backfill, run_continuous
                import yaml as _yaml
                with open(config_path) as f:
                    demo_config = _yaml.safe_load(f)
                inventory = build_inventory(demo_config)
                backfill_min = demo_config.get("demo", {}).get("backfill_minutes", 30)
                backfill(inventory, backfill_min)
                print()
                print("  Backfill complete. Starting continuous push...")
                print("  Ctrl+C to stop data generation (stack keeps running).")
                print()
                run_continuous(inventory)
            except KeyboardInterrupt:
                print("\n  Demo data stopped. Stack is still running.")
            except ImportError as exc:
                print(f"  ERROR importing demo_data_generator: {exc}")
                print("  Ensure PyYAML is installed: pip install pyyaml")
    else:
        print()
        print("  Next steps:")
        print("    1. Open Grafana at http://localhost:3000")
        print("    2. Check dashboards under Dashboards menu")
        print("    3. (Optional) Run with demo data:")
        print("       python scripts/stack_manage.py --demo-data")
        print("    4. Stop stack: python scripts/stack_manage.py --stop")

    return 0


if __name__ == "__main__":
    sys.exit(main())
