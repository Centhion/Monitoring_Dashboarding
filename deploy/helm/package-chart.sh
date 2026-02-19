#!/usr/bin/env bash
# =============================================================================
# Helm Chart Packaging Script
# =============================================================================
# Copies config files from the repo root into the chart's files/ directory,
# then runs helm package. This ensures the chart bundles the same configs
# used by Docker Compose (single source of truth).
#
# Usage (from repo root):
#   ./deploy/helm/package-chart.sh
#   ./deploy/helm/package-chart.sh --output-dir /tmp/charts
#
# The files/ directory is gitignored -- it is populated only at package time.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHART_DIR="${SCRIPT_DIR}/monitoring-stack"
FILES_DIR="${CHART_DIR}/files"

echo "Packaging monitoring-stack Helm chart..."
echo "  Repo root:  ${REPO_ROOT}"
echo "  Chart dir:  ${CHART_DIR}"
echo ""

# Clean previous files
rm -rf "${FILES_DIR:?}"/*
mkdir -p "${FILES_DIR}/dashboards/windows"
mkdir -p "${FILES_DIR}/dashboards/linux"
mkdir -p "${FILES_DIR}/dashboards/overview"

# Copy Prometheus configs
echo "  Copying Prometheus configs..."
cp "${REPO_ROOT}/configs/prometheus/recording_rules.yml" "${FILES_DIR}/recording_rules.yml"

# Copy alert rules
echo "  Copying alert rules..."
cp "${REPO_ROOT}/alerts/prometheus/windows_alerts.yml" "${FILES_DIR}/windows_alerts.yml"
cp "${REPO_ROOT}/alerts/prometheus/linux_alerts.yml" "${FILES_DIR}/linux_alerts.yml"
cp "${REPO_ROOT}/alerts/prometheus/infra_alerts.yml" "${FILES_DIR}/infra_alerts.yml"
cp "${REPO_ROOT}/alerts/prometheus/role_alerts.yml" "${FILES_DIR}/role_alerts.yml"

# Copy Loki config
echo "  Copying Loki config..."
cp "${REPO_ROOT}/configs/loki/loki.yml" "${FILES_DIR}/loki.yml"

# Copy Alertmanager config and templates
echo "  Copying Alertmanager config..."
cp "${REPO_ROOT}/configs/alertmanager/alertmanager.yml" "${FILES_DIR}/alertmanager.yml"
cp "${REPO_ROOT}/configs/alertmanager/templates/teams.tmpl" "${FILES_DIR}/teams.tmpl"

# Copy Grafana notifier provisioning
echo "  Copying Grafana provisioning..."
cp "${REPO_ROOT}/configs/grafana/notifiers/notifiers.yml" "${FILES_DIR}/notifiers.yml"

# Copy dashboard JSON files
echo "  Copying dashboard JSON..."
cp "${REPO_ROOT}/dashboards/windows/"*.json "${FILES_DIR}/dashboards/windows/" 2>/dev/null || echo "    No Windows dashboards found"
cp "${REPO_ROOT}/dashboards/linux/"*.json "${FILES_DIR}/dashboards/linux/" 2>/dev/null || echo "    No Linux dashboards found"
cp "${REPO_ROOT}/dashboards/overview/"*.json "${FILES_DIR}/dashboards/overview/" 2>/dev/null || echo "    No Overview dashboards found"

echo ""
echo "  Files staged in: ${FILES_DIR}"
echo ""

# Run helm package
HELM_ARGS=("${CHART_DIR}")
if [[ "${1:-}" == "--output-dir" && -n "${2:-}" ]]; then
    HELM_ARGS+=("--destination" "${2}")
fi

echo "  Running: helm package ${HELM_ARGS[*]}"
helm package "${HELM_ARGS[@]}"

echo ""
echo "Chart packaged successfully."
