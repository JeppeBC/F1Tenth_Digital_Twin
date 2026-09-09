# Not a DTaaS lifecycle phase - a convenience command for PowerShell users.
# Stops BOTH the base DTaaS stack and the F1Tenth overlay together, so a
# plain `docker compose down` from workspace-dex-localhost/ (which only
# knows its own docker-compose.yml) doesn't leave f1tenth-dt/influxdb/
# grafana running behind on their own ports.
#
# Reads DTAAS_DIR (and PT_HOST) from digital_twins/f1tenth/config/dt.env -
# the same file the Bash lifecycle scripts use. Run from anywhere:
#   powershell -File dtaas\down-all.ps1

$ErrorActionPreference = "Stop"
$dtaasRoot = $PSScriptRoot

$envFile = Join-Path $dtaasRoot "digital_twins\f1tenth\config\dt.env"
if (-not (Test-Path $envFile)) {
    $envFile = Join-Path $dtaasRoot "digital_twins\f1tenth\config\dt.env.example"
    Write-Warning "dt.env not found - using dt.env.example defaults. Copy it to dt.env and edit DTAAS_DIR/PT_HOST for your machine."
}

$config = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?([^"]*?)"?\s*$') {
        $config[$matches[1]] = $matches[2]
    }
}

if (-not $config.ContainsKey('DTAAS_DIR')) {
    throw "DTAAS_DIR not set in $envFile"
}

$dtaasComposeFile = Join-Path $config['DTAAS_DIR'] "docker-compose.yml"
$overlayComposeFile = Join-Path $dtaasRoot "compose\docker-compose.f1tenth.yml"

if (-not (Test-Path $dtaasComposeFile)) {
    throw "DTAAS_DIR in $envFile has no docker-compose.yml: $dtaasComposeFile"
}

# Same fix as _common.sh: Compose resolves the overlay's relative bind mounts
# against the *base* file's directory, not its own, so docker-compose.f1tenth.yml
# uses this absolute path instead.
$env:F1TENTH_DIR_WIN = $dtaasRoot -replace '\\', '/'
if ($config.ContainsKey('PT_HOST') -and $config['PT_HOST']) {
    $env:PT_HOST = $config['PT_HOST']
}

docker compose -f "$dtaasComposeFile" -f "$overlayComposeFile" down
