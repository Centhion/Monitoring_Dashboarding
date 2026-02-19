# Convenience wrapper to run docker compose from the repo root.
# Avoids typing the full -f path for every command.
#
# Usage (from repo root):
#   .\dc.ps1 up -d           Start the stack
#   .\dc.ps1 logs -f          Stream logs
#   .\dc.ps1 restart grafana  Restart a service
#   .\dc.ps1 down -v          Stop and remove volumes

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $ScriptDir "deploy\docker\docker-compose.yml"
$EnvFile = Join-Path $ScriptDir ".env"

$BaseArgs = @("-f", $ComposeFile)
if (Test-Path $EnvFile) {
    $BaseArgs += @("--env-file", $EnvFile)
}

& docker compose @BaseArgs @args
