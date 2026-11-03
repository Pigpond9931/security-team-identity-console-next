$ErrorActionPreference = 'Stop'
$taskToolDir = Join-Path $PSScriptRoot 'tools'
New-Item -ItemType Directory -Force -Path $taskToolDir | Out-Null
$taskDestination = Join-Path $taskToolDir 'cloudflared.exe'
if (Test-Path -LiteralPath $taskDestination) { throw 'Ya existe tools/cloudflared.exe. Verifica su versión antes de reemplazarlo.' }
$taskDownload = Join-Path $taskToolDir 'cloudflared.download'
Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/download/2026.10.1/cloudflared-windows-amd64.exe' -OutFile $taskDownload
$taskDigest = (Get-FileHash -LiteralPath $taskDownload -Algorithm SHA256).Hash.ToLowerInvariant()
if ($taskDigest -ne '4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6') { throw 'El hash no coincide; no se instala ni ejecuta el archivo.' }
Move-Item -LiteralPath $taskDownload -Destination $taskDestination
Write-Output 'Cloudflared oficial instalado y hash verificado.'
