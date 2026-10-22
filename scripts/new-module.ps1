param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Dest = (Join-Path (Split-Path -Parent $PSScriptRoot) 'custom-addons')
)

$odooDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'odoo'
Push-Location $odooDir
try {
    python odoo-bin scaffold $Name $Dest
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Created module '$Name' in $Dest"
Write-Host "Next steps:"
Write-Host "  1. Replace generated security/ir.model.access.csv with security/ir.access.csv (Odoo 20 format)."
Write-Host "  2. Remove unused controllers/, demo/, views/templates.xml."
Write-Host "  3. Add the module name to depends and data in __manifest__.py."
Write-Host "  4. Install with: python odoo-bin -c odoo.conf -d odoo-crm -i $Name --stop-after-init"
