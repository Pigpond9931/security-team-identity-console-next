[CmdletBinding(SupportsShouldProcess)]
param([switch]$RestartChild)
$ErrorActionPreference='Stop'
# Parada cooperativa: el lanzador cierra exclusivamente sus propios hijos.
# No depende de CIM ni termina procesos mediante un PID potencialmente viejo.
if($PSCmdlet.ShouldProcess('SECURITY TEAM Cloudflare','Solicitar parada')){
    if(-not $RestartChild){Set-Content -LiteralPath (Join-Path $PSScriptRoot 'data\cloudflare-supervisor.stop') -Value 'stop'}
    Set-Content -LiteralPath (Join-Path $PSScriptRoot 'data\cloudflare-child.stop') -Value 'stop'
    Write-Host 'Parada solicitada. El lanzador cerrara su servidor y sus tuneles.'
}
