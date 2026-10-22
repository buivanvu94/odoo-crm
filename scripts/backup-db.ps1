param(
    [string]$Database = 'odoo-crm',
    [string]$Container = 'odoo-crm-db',
    [string]$OutDir = (Join-Path (Split-Path -Parent $PSScriptRoot) 'backups')
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$file = Join-Path $OutDir ("{0}-{1}.dump" -f $Database, (Get-Date -Format 'yyyyMMdd-HHmmss'))

# Use cmd redirection: PowerShell text redirection corrupts binary dumps.
cmd /c "docker exec $Container pg_dump -U odoo -Fc $Database > `"$file`""

if ($LASTEXITCODE -eq 0) {
    $size = (Get-Item $file).Length / 1MB
    Write-Host ("Backup OK: {0} ({1:N1} MB)" -f $file, $size)
} else {
    Write-Error "pg_dump failed with exit code $LASTEXITCODE"
}
