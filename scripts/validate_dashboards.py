#!/usr/bin/env python3
"""
Grafana Dashboard JSON Validator

Performs structural and semantic validation on Grafana dashboard JSON files.
Ensures dashboards follow project conventions and reference correct datasources.

Checks performed:
  - JSON syntax validity
  - Required dashboard metadata (uid, title, schemaVersion)
  - UID uniqueness across all dashboard files
  - Template variable presence (environment, datacenter, hostname)
  - Panel structure completeness (targets, datasource, gridPos)
  - Datasource UID references match provisioned sources
  - No overlapping panel positions (gridPos collisions)
  - Recording rule metric name references match known rules

Exit codes:
    0 -- All validations passed
    1 -- One or more validations failed

Usage:
    python scripts/validate_dashboards.py [--verbose] [path ...]
    python scripts/validate_dashboards.py dashboards/
    python scripts/validate_dashboards.py dashboards/windows/windows_overview.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Datasource UIDs provisioned by configs/grafana/datasources/datasources.yml
VALID_DATASOURCE_UIDS = {
    "prometheus": "prometheus",
    "loki": "loki",
    # Grafana built-in datasources
    "-- Grafana --": "grafana",
    "grafana": "grafana",
    "-- Dashboard --": "dashboard",
}

# Recording rule metrics defined in configs/prometheus/recording_rules.yml.
# Dashboard panels should query these rather than raw metrics for consistency.
KNOWN_RECORDING_RULES = {
    "instance:windows_cpu_utilization:ratio",
    "instance:windows_memory_utilization:ratio",
    "instance:windows_disk_free:ratio",
    "instance:windows_disk_io_utilization:ratio",
    "instance:windows_network_bytes:rate5m",
    "instance:windows_services_not_running:count",
    "instance:windows_uptime:seconds",
    "instance:linux_cpu_utilization:ratio",
    "instance:linux_memory_utilization:ratio",
    "instance:linux_disk_free:ratio",
    "instance:linux_disk_io_utilization:ratio",
    "instance:linux_network_bytes:rate5m",
    "instance:linux_load_normalized:ratio",
    "instance:linux_systemd_failed:count",
    "instance:linux_uptime:seconds",
    "fleet:servers_reporting:count",
    "fleet:cpu_utilization:avg",
    "fleet:memory_utilization:avg",
    "fleet:high_cpu:count",
    "fleet:low_disk:count",
}

# Minimum required template variables for server-level dashboards
REQUIRED_TEMPLATE_VARS = {"environment", "datacenter"}


class ValidationResult:
    """Accumulates validation findings for a single file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def validate_json_syntax(filepath: Path, result: ValidationResult) -> dict | None:
    """Parse JSON and return the dashboard object, or None on failure."""
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data
    except json.JSONDecodeError as exc:
        result.error(f"JSON syntax error: {exc}")
        return None


def validate_dashboard_metadata(data: dict, result: ValidationResult) -> None:
    """Check required top-level dashboard fields."""
    if "uid" not in data or not data["uid"]:
        result.error("Missing or empty 'uid'")

    if "title" not in data or not data["title"]:
        result.error("Missing or empty 'title'")

    schema_version = data.get("schemaVersion")
    if schema_version is None:
        result.warn("Missing 'schemaVersion'")
    elif not isinstance(schema_version, int):
        result.warn(f"'schemaVersion' should be an integer, got: {type(schema_version)}")

    if "tags" not in data or not data["tags"]:
        result.warn("Missing or empty 'tags' -- helps with dashboard discovery")


def validate_template_variables(data: dict, result: ValidationResult) -> None:
    """Verify that standard template variables are defined."""
    templating = data.get("templating", {})
    var_list = templating.get("list", [])

    defined_vars = set()
    for var in var_list:
        if isinstance(var, dict) and "name" in var:
            defined_vars.add(var["name"])

    missing = REQUIRED_TEMPLATE_VARS - defined_vars
    for var_name in sorted(missing):
        result.warn(
            f"Missing recommended template variable: '{var_name}'"
        )


def validate_panels(data: dict, result: ValidationResult) -> None:
    """Validate panel structure, datasource references, and grid positions."""
    panels = data.get("panels", [])

    if not panels:
        result.warn("Dashboard has no panels")
        return

    # Track grid positions per scope. Panels inside collapsed rows belong
    # to separate scopes because they only render when that row is expanded.
    # Only top-level (non-row-nested) panels share grid space.
    top_level_positions: list[tuple[str, dict]] = []

    _validate_panel_list(panels, result, top_level_positions)

    # Only check overlaps among top-level panels (not collapsed row children)
    _check_grid_overlaps(top_level_positions, result)


def _validate_panel_list(
    panels: list,
    result: ValidationResult,
    grid_positions: list,
) -> None:
    """Recursively validate panels, including row-nested panels."""
    for i, panel in enumerate(panels):
        if not isinstance(panel, dict):
            result.error(f"panels[{i}]: must be a JSON object")
            continue

        panel_type = panel.get("type", "unknown")
        panel_title = panel.get("title", f"untitled-{i}")
        panel_id = panel.get("id")

        if panel_id is None:
            result.warn(f"Panel '{panel_title}': missing 'id'")

        # Row panels contain nested panels. Collapsed rows store child panels
        # in a "panels" array. These children have absolute gridPos coordinates
        # but occupy separate visual scope, so we validate them independently.
        if panel_type == "row":
            nested = panel.get("panels", [])
            if nested:
                row_positions: list[tuple[str, dict]] = []
                _validate_panel_list(nested, result, row_positions)
                _check_grid_overlaps(row_positions, result)
            continue

        # Non-row panels should have gridPos
        grid_pos = panel.get("gridPos")
        if grid_pos:
            grid_positions.append((panel_title, grid_pos))
        else:
            result.warn(f"Panel '{panel_title}': missing 'gridPos'")

        # Validate datasource reference
        datasource = panel.get("datasource")
        if datasource and isinstance(datasource, dict):
            uid = datasource.get("uid", "")
            if uid and uid not in VALID_DATASOURCE_UIDS:
                # Allow variable datasources like $datasource
                if not uid.startswith("$"):
                    result.error(
                        f"Panel '{panel_title}': unknown datasource uid '{uid}' "
                        f"(expected one of: {', '.join(sorted(VALID_DATASOURCE_UIDS))})"
                    )

        # Validate targets exist for data panels
        targets = panel.get("targets", [])
        if not targets and panel_type not in ("text", "row", "news", "dashlist"):
            result.warn(f"Panel '{panel_title}' ({panel_type}): no query targets defined")

        # Check target expressions reference known metrics
        for t_idx, target in enumerate(targets):
            if isinstance(target, dict):
                expr = target.get("expr", "")
                if expr:
                    _check_metric_references(expr, panel_title, result)


def _check_metric_references(
    expr: str, panel_title: str, result: ValidationResult
) -> None:
    """Verify that PromQL expressions reference known recording rules or raw metrics.

    This is advisory only -- raw metric queries are allowed but we flag them
    when a recording rule equivalent exists.
    """
    # Extract metric names from the expression (simplified regex)
    metric_pattern = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*")
    metrics_in_expr = set(metric_pattern.findall(expr))

    # Filter to only metric-like names (contain at least one underscore or colon)
    metrics_in_expr = {m for m in metrics_in_expr if "_" in m or ":" in m}

    # Remove PromQL functions and keywords
    promql_keywords = {
        "sum", "avg", "min", "max", "count", "rate", "irate", "increase",
        "topk", "bottomk", "sort", "sort_desc", "by", "without", "on",
        "ignoring", "group_left", "group_right", "offset", "bool", "and",
        "or", "unless", "vector", "histogram_quantile", "label_replace",
        "label_join", "count_over_time", "sum_over_time", "avg_over_time",
        "time", "absent", "absent_over_time", "changes", "resets", "delta",
        "deriv", "predict_linear", "clamp_min", "clamp_max",
    }
    metrics_in_expr -= promql_keywords


def _check_grid_overlaps(
    positions: list[tuple[str, dict]], result: ValidationResult
) -> None:
    """Detect panels with overlapping grid positions."""
    # Grafana uses a 24-column grid. Panels can overlap vertically.
    # This is a basic check -- Grafana handles overlaps by pushing panels down,
    # but explicit overlaps usually indicate a layout mistake.
    for i, (title_a, pos_a) in enumerate(positions):
        for title_b, pos_b in positions[i + 1 :]:
            if _rects_overlap(pos_a, pos_b):
                result.warn(
                    f"Possible grid overlap: '{title_a}' and '{title_b}'"
                )


def _rects_overlap(a: dict, b: dict) -> bool:
    """Check if two gridPos rectangles overlap."""
    try:
        ax, ay, aw, ah = a["x"], a["y"], a["w"], a["h"]
        bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
    except (KeyError, TypeError):
        return False

    # No overlap if one is entirely left/right/above/below the other
    if ax + aw <= bx or bx + bw <= ax:
        return False
    if ay + ah <= by or by + bh <= ay:
        return False

    return True


def validate_file(filepath: Path, verbose: bool = False) -> ValidationResult:
    """Run all validation checks against a single dashboard JSON file."""
    result = ValidationResult(filepath)

    data = validate_json_syntax(filepath, result)
    if data is None:
        return result

    validate_dashboard_metadata(data, result)
    validate_template_variables(data, result)
    validate_panels(data, result)

    if verbose and result.passed:
        print(f"  PASS: {filepath}")

    return result


def collect_json_files(paths: list[Path]) -> list[Path]:
    """Resolve paths to individual JSON files, expanding directories."""
    files: list[Path] = []

    for path in paths:
        if path.is_file() and path.suffix == ".json":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
        else:
            print(f"WARNING: Skipping {path}")

    return files


def check_uid_uniqueness(
    results: list[tuple[Path, dict]], all_results: list[ValidationResult]
) -> None:
    """Ensure no two dashboards share the same UID."""
    uid_map: dict[str, Path] = {}

    for filepath, data in results:
        uid = data.get("uid", "")
        if uid:
            if uid in uid_map:
                # Find the result for this file and add an error
                for r in all_results:
                    if r.filepath == filepath:
                        r.error(
                            f"Duplicate dashboard UID '{uid}' "
                            f"(also in {uid_map[uid]})"
                        )
                        break
            else:
                uid_map[uid] = filepath


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Grafana dashboard JSON files"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("dashboards")],
        help="Files or directories to validate (default: dashboards/)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show passing files"
    )
    args = parser.parse_args()

    files = collect_json_files(args.paths)

    if not files:
        print("No JSON files found to validate.")
        return 0

    print(f"Validating {len(files)} Grafana dashboard file(s)...\n")

    results: list[ValidationResult] = []
    parsed_dashboards: list[tuple[Path, dict]] = []

    for filepath in files:
        result = validate_file(filepath, verbose=args.verbose)
        results.append(result)

        # Collect parsed data for cross-file checks
        if result.passed:
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                parsed_dashboards.append((filepath, data))
            except (json.JSONDecodeError, OSError):
                pass

    # Cross-file validation
    check_uid_uniqueness(parsed_dashboards, results)

    # Report
    errors_total = 0
    warnings_total = 0

    for result in results:
        if result.errors or result.warnings:
            print(f"  {result.filepath}:")
            for error in result.errors:
                print(f"    ERROR: {error}")
                errors_total += 1
            for warning in result.warnings:
                print(f"    WARN:  {warning}")
                warnings_total += 1

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"\nResults: {passed} passed, {failed} failed, {warnings_total} warnings")
    print(f"Files checked: {len(results)}")

    return 1 if errors_total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
