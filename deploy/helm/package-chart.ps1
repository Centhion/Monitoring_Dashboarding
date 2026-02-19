# =============================================================================
# Helm Chart Packaging Script (Windows)
# =============================================================================
# Copies config files from the repo root into the chart's files/ directory,
# then runs helm package. This ensures the chart bundles the same configs
# used by Docker Compose (single source of truth).
#
# Usage (from repo root):
#   .\deploy\helm\package-chart.ps1
#   .\deploy\helm\package-chart.ps1 -OutputDir C:\tmp\charts
# =============================================================================

param(
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$ChartDir = Join-Path $ScriptDir "monitoring-stack"
$FilesDir = Join-Path $ChartDir "files"

Write-Host "Packaging monitoring-stack Helm chart..."
Write-Host "  Repo root:  $RepoRoot"
Write-Host "  Chart dir:  $ChartDir"
Write-Host ""

# Clean previous files
if (Test-Path $FilesDir) {
    Get-ChildItem $FilesDir -Exclude ".gitkeep" | Remove-Item -Recurse -Force
}
New-Item -ItemType Directory -Path "$FilesDir\dashboards\windows" -Force | Out-Null
New-Item -ItemType Directory -Path "$FilesDir\dashboards\linux" -Force | Out-Null
New-Item -ItemType Directory -Path "$FilesDir\dashboards\overview" -Force | Out-Null

# Copy Prometheus configs
Write-Host "  Copying Prometheus configs..."
Copy-Item "$RepoRoot\configs\prometheus\recording_rules.yml" "$FilesDir\recording_rules.yml"

# Copy alert rules
Write-Host "  Copying alert rules..."
Copy-Item "$RepoRoot\alerts\prometheus\windows_alerts.yml" "$FilesDir\windows_alerts.yml"
Copy-Item "$RepoRoot\alerts\prometheus\linux_alerts.yml" "$FilesDir\linux_alerts.yml"
Copy-Item "$RepoRoot\alerts\prometheus\infra_alerts.yml" "$FilesDir\infra_alerts.yml"
Copy-Item "$RepoRoot\alerts\prometheus\role_alerts.yml" "$FilesDir\role_alerts.yml"

# Copy Loki config
Write-Host "  Copying Loki config..."
Copy-Item "$RepoRoot\configs\loki\loki.yml" "$FilesDir\loki.yml"

# Copy Alertmanager config and templates
Write-Host "  Copying Alertmanager config..."
Copy-Item "$RepoRoot\configs\alertmanager\alertmanager.yml" "$FilesDir\alertmanager.yml"
Copy-Item "$RepoRoot\configs\alertmanager\templates\teams.tmpl" "$FilesDir\teams.tmpl"

# Copy Grafana notifier provisioning
Write-Host "  Copying Grafana provisioning..."
Copy-Item "$RepoRoot\configs\grafana\notifiers\notifiers.yml" "$FilesDir\notifiers.yml"

# Copy dashboard JSON files
Write-Host "  Copying dashboard JSON..."
$dashDirs = @("windows", "linux", "overview")
foreach ($dir in $dashDirs) {
    $src = Join-Path $RepoRoot "dashboards\$dir"
    $dst = Join-Path $FilesDir "dashboards\$dir"
    if (Test-Path "$src\*.json") {
        Copy-Item "$src\*.json" $dst
    } else {
        Write-Host "    No $dir dashboards found"
    }
}

Write-Host ""
Write-Host "  Files staged in: $FilesDir"
Write-Host ""

# Run helm package
$helmArgs = @($ChartDir)
if ($OutputDir) {
    $helmArgs += @("--destination", $OutputDir)
}

Write-Host "  Running: helm package $($helmArgs -join ' ')"
& helm package @helmArgs

Write-Host ""
Write-Host "Chart packaged successfully."
