[CmdletBinding(SupportsShouldProcess)]
param()
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'runtime_paths.ps1')
$stDataDirectory = Get-STDataDirectory
$env:PSModulePath=Join-Path $PSHOME 'Modules'
$recordFile=Join-Path $stDataDirectory 'share-processes.json'
if (-not (Test-Path -LiteralPath $recordFile)) { Write-Host 'No hay un tunel de esta aplicacion registrado.'; exit 0 }
$record=Get-Content -LiteralPath $recordFile -Raw | ConvertFrom-Json
$agentId=[int]$record.agent
$candidate=Get-CimInstance Win32_Process -Filter "ProcessId = $agentId"
if ($null -eq $candidate) { Write-Host 'El agente ya esta detenido.'; exit 0 }
$expected=Join-Path $PSScriptRoot 'tools\ngrok.exe'
$policy=Join-Path $stDataDirectory 'ngrok-policy.json'
if (-not ($candidate.CommandLine.Contains($expected) -and $candidate.CommandLine.Contains($policy))) { throw 'El agente no coincide con esta aplicacion. No se detuvo.' }
$started=(Get-Process -Id $agentId).StartTime.ToUniversalTime()
$registered=[DateTimeOffset]::FromUnixTimeMilliseconds([long]$record.registered_ms).UtcDateTime
if ($started -gt $registered.AddSeconds(1)) { throw 'El identificador del agente fue reutilizado. No se detuvo.' }
if ($PSCmdlet.ShouldProcess("Ngrok de SECURITY TEAM PID $agentId",'Cerrar tunel')) {
    Stop-Process -Id $agentId
    Write-Host 'Tunel cerrado. El asistente detendra tambien su servidor.'
}
