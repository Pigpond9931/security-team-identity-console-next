[CmdletBinding(SupportsShouldProcess)]
param()
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME 'Modules'
$recordFile=Join-Path $PSScriptRoot 'data\server-process.json'
if (-not (Test-Path -LiteralPath $recordFile)) { Write-Host 'No hay un servidor registrado por esta version.'; exit 0 }
$record=Get-Content -LiteralPath $recordFile -Raw | ConvertFrom-Json
$processId=[int]$record.pid
$candidate=Get-CimInstance Win32_Process -Filter "ProcessId = $processId"
$expected=Join-Path $PSScriptRoot 'server.py'
if ($null -eq $candidate) { Write-Host 'El servidor ya esta detenido.'; exit 0 }
if (-not $candidate.CommandLine.Contains($expected)) { throw 'El proceso no coincide con esta aplicacion. No se detuvo.' }
$started=(Get-Process -Id $processId).StartTime.ToUniversalTime()
$registered=[DateTimeOffset]::FromUnixTimeMilliseconds([long]$record.registered_ms).UtcDateTime
if ($started -gt $registered.AddSeconds(1)) { throw 'El identificador fue reutilizado por otro proceso. No se detuvo.' }
if ($PSCmdlet.ShouldProcess("SECURITY TEAM PID $processId",'Detener')) {
    Stop-Process -Id $processId
    Write-Host 'Servidor de SECURITY TEAM detenido.'
}
