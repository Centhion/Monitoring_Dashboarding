#!/usr/bin/env python3
"""
Monitoring Stack Manager

One-command startup for the Docker Compose monitoring stack. Validates
prerequisites, starts services, waits for health checks, and verifies
the full stack is operational.

Supports two deployment modes:
  - Production: Grafana connects to real SCOM DW via .env configuration.
                Prometheus/Loki dashboards populate when Alloy agents are deployed.
  - SCOM Demo:  Includes Azure SQL Edge simulator with auto-seeded synthetic data.
                All SCOM dashboards render immediately. No production access needed.

Usage:
    python scripts/stack_manage.py                  Start stack (production mode)
    python scripts/stack_manage.py --scom-demo      Start stack with SCOM simulator
    python scripts/stack_manage.py --status          Check health of running stack
    python scripts/stack_manage.py --stop            Stop stack (preserve data)
    python scripts/stack_manage.py --reset           Stop stack and delete all data
    python scripts/stack_manage.py --demo-data       Start with Prometheus/Loki demo data
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

# Service endpoints for health checking.
# Core services are always started. SCOM simulator services are only
# started when --scom-demo is used.
CORE_SERVICES = {
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

    # .env file exists (optional but recommended for production SCOM DW connection)
    if ENV_FILE.exists():
        print("  .env: found")
    else:
        print("  .env: not found (using defaults)")

    return True


def _compose_base_cmd(scom_demo: bool = False) -> list[str]:
    """Build the base docker compose command with file, env-file, and profile flags.

    Args:
        scom_demo: If True, include the scom-demo profile which starts the
                   Azure SQL Edge simulator and auto-seed container alongside
                   the core monitoring stack.
    """
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    if ENV_FILE.exists():
        cmd.extend(["--env-file", str(ENV_FILE)])
    if scom_demo:
        cmd.extend(["--profile", "scom-demo"])
    return cmd


def start_stack(scom_demo: bool = False) -> bool:
    """Start the Docker Compose stack.

    Args:
        scom_demo: If True, include the SCOM DW simulator (Azure SQL Edge)
                   and the auto-seed container. The seed container waits for
                   SQL Edge to be ready, then populates synthetic data for
                   all SCOM dashboards (~8 minutes for 411K rows).
    """
    if scom_demo:
        print("\nStarting monitoring stack with SCOM simulator...")
    else:
        print("\nStarting monitoring stack...")

    cmd = _compose_base_cmd(scom_demo=scom_demo) + ["up", "-d"]
    code, output = run_command(cmd, cwd=PROJECT_ROOT)
    if code != 0:
        print(f"  ERROR: Failed to start stack:\n{output}")
        return False
    print("  Containers starting...")
    return True


def wait_for_health(timeout_seconds: int = 120, scom_demo: bool = False) -> bool:
    """Wait for all services to pass health checks.

    Checks core services (Prometheus, Loki, Alertmanager, Grafana). When
    scom_demo is True, also waits for the SCOM seed container to finish
    populating the simulator database.
    """
    print(f"\nWaiting for services to become healthy (timeout: {timeout_seconds}s)...")

    start = time.monotonic()
    healthy = set()

    while time.monotonic() - start < timeout_seconds:
        for name, svc in CORE_SERVICES.items():
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

        if len(healthy) == len(CORE_SERVICES):
            break

        time.sleep(2)

    # Report any unhealthy core services
    unhealthy = set(CORE_SERVICES.keys()) - healthy
    for name in unhealthy:
        print(f"  {name}: TIMEOUT -- not healthy after {timeout_seconds}s")

    if unhealthy:
        return False

    # If SCOM demo mode, check the seed container status
    if scom_demo:
        print("\n  SCOM simulator seeding in progress...")
        print("  (This takes ~8 minutes on first run. Dashboards will populate when complete.)")
        _check_scom_seed_status()

    return True


def _check_scom_seed_status() -> None:
    """Check if the SCOM seed container has finished populating data.

    Non-blocking -- reports current status but does not wait for completion.
    The seed runs in the background and dashboards will show data once it finishes.
    """
    code, output = run_command([
        "docker", "inspect", "mon-scom-dw-seed",
        "--format", "{{.State.Status}} {{.State.ExitCode}}"
    ])
    if code != 0:
        print("  SCOM seed container: not found (may still be starting)")
        return

    parts = output.strip().split()
    status = parts[0] if parts else "unknown"
    exit_code = parts[1] if len(parts) > 1 else "?"

    if status == "exited" and exit_code == "0":
        print("  SCOM seed: complete")
    elif status == "running":
        print("  SCOM seed: still running (dashboards will populate when done)")
        print("  Monitor progress: docker logs -f mon-scom-dw-seed")
    else:
        print(f"  SCOM seed: {status} (exit code {exit_code})")
        print("  Check logs: docker logs mon-scom-dw-seed")


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

        # Core datasources always expected
        expected_uids = {"prometheus", "loki"}
        actual_uids = {ds.get("uid", "") for ds in datasources}
        missing = expected_uids - actual_uids

        if missing:
            print(f"  WARNING: Missing expected datasources: {missing}")
            return False

        # Report SCOM DW datasource if present
        if "scom-dw" in actual_uids:
            print("  SCOM Data Warehouse: provisioned")

        print(f"  All expected datasources provisioned")
        return True

    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"  ERROR: Could not query Grafana API: {exc}")
        return False


def print_status() -> None:
    """Print current health status of all services."""
    print("\nMonitoring Stack Status")
    print("=" * 50)

    all_healthy = True
    for name, svc in CORE_SERVICES.items():
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

    # Check SCOM simulator containers (may not be running in production mode)
    for container in ["mon-scom-dw-sim", "mon-scom-dw-seed"]:
        code, output = run_command([
            "docker", "inspect", container,
            "--format", "{{.State.Status}}"
        ])
        if code == 0:
            status = output.strip()
            label = container.replace("mon-", "")
            print(f"  {label:15s}  {status.upper()}")

    print("=" * 50)
    if all_healthy:
        print("  All services healthy")
    else:
        print("  Some services unhealthy -- check logs with:")
        print(f"    docker compose -f {COMPOSE_FILE} logs <service-name>")


def stop_stack(remove_volumes: bool = False, scom_demo: bool = False) -> None:
    """Stop the Docker Compose stack.

    Args:
        remove_volumes: If True, also delete persistent data volumes.
                        Use this for a full reset (fresh start).
        scom_demo: If True, include the scom-demo profile so simulator
                   containers are also stopped and removed.
    """
    cmd = _compose_base_cmd(scom_demo=scom_demo) + ["down"]
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
        description="Manage the Docker Compose monitoring stack"
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
        "--scom-demo", action="store_true",
        help="Include SCOM DW simulator with synthetic data (for demos without production access)"
    )
    parser.add_argument(
        "--demo-data", action="store_true",
        help="After startup, backfill and stream Prometheus/Loki demo data for showcasing dashboards"
    )
    args = parser.parse_args()

    # Determine if SCOM demo mode is active.
    # For stop/reset, we always include the profile so simulator containers
    # are also cleaned up if they were running.
    scom_demo = args.scom_demo

    if args.status:
        print_status()
        return 0

    if args.stop:
        # Include scom-demo profile on stop so simulator containers are also stopped
        stop_stack(remove_volumes=False, scom_demo=True)
        return 0

    if args.reset:
        # Include scom-demo profile on reset so simulator volumes are also removed
        stop_stack(remove_volumes=True, scom_demo=True)
        return 0

    # --- Full startup flow ---
    print("=" * 50)
    if scom_demo:
        print("  Monitoring Stack Setup (SCOM Demo Mode)")
    else:
        print("  Monitoring Stack Setup")
    print("=" * 50)

    if not check_prerequisites():
        return 1

    if not start_stack(scom_demo=scom_demo):
        return 1

    if not wait_for_health(timeout_seconds=120, scom_demo=scom_demo):
        print("\nSome services failed to start. Check logs:")
        compose_cmd = f"docker compose -f {COMPOSE_FILE}"
        print(f"  {compose_cmd} logs prometheus")
        print(f"  {compose_cmd} logs loki")
        print(f"  {compose_cmd} logs grafana")
        if scom_demo:
            print(f"  {compose_cmd} logs scom-dw-sim")
            print(f"  {compose_cmd} logs scom-dw-seed")
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

    if scom_demo:
        print()
        print("  SCOM Demo:")
        print("    SCOM dashboards in 'SCOM Monitoring' folder")
        print("    Synthetic data seeding in background (~8 min)")
        print("    Monitor: docker logs -f mon-scom-dw-seed")

    print()

    if rules_ok and datasources_ok:
        print("  All validations passed.")
    else:
        print("  Some validations had warnings -- check output above.")

    # Prometheus/Loki demo data mode
    if args.demo_data:
        print()
        print("Starting Prometheus/Loki demo data generator...")
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
        if not scom_demo:
            print("    3. (Optional) Run with SCOM demo data:")
            print("       python scripts/stack_manage.py --scom-demo")
            print("    4. (Optional) Run with Prometheus/Loki demo data:")
            print("       python scripts/stack_manage.py --demo-data")
        print(f"    Stop stack: python scripts/stack_manage.py --stop")
        print(f"    Full reset: python scripts/stack_manage.py --reset")

    return 0


if __name__ == "__main__":
    sys.exit(main())
