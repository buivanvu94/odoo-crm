param(
    [int]$Port = 8069,
    [switch]$FullReload
)

$odooDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'odoo'
$dev = if ($FullReload) { 'all' } else { 'qweb,xml' }

if ($FullReload) {
    python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('watchdog') else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "watchdog is not installed. Python auto-reload will not work. Run: pip install watchdog"
    }
}

Push-Location $odooDir
try {
    python odoo-bin -c odoo.conf --http-port=$Port --dev=$dev
} finally {
    Pop-Location
}
