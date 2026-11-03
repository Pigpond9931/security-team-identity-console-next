$ErrorActionPreference='Stop'
$file=Join-Path $PSScriptRoot 'data\cloudflare-links.json'
if(-not(Test-Path -LiteralPath $file)){Write-Host 'Inicia primero COMPARTIR_CLOUDFLARE.cmd';exit 1}
$links=Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
$url=[Uri]$links.console_url
if($url.Scheme -ne 'https' -or -not $url.Host.EndsWith('.trycloudflare.com')){throw 'Direccion no valida.'}
if(-not(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'data\cloudflare-processes.json'))){Write-Host 'El enlace anterior ya no esta activo. Inicia COMPARTIR_CLOUDFLARE.cmd';exit 1}
Write-Host ('Enlace para compartir: '+$url.AbsoluteUri)
Start-Process $url.AbsoluteUri
