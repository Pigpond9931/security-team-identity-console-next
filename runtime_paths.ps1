# Use exactly the same resolver as Python; no mkdir, migration or credential output.
function Get-STDataDirectory {
    $pythonExecutable = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExecutable)) {
        throw 'Falta el entorno Python local. Ejecuta INSTALAR.cmd antes de usar este lanzador.'
    }
    $resolved = & $pythonExecutable (Join-Path $PSScriptRoot 'runtime_paths.py') --print
    if ($LASTEXITCODE -ne 0 -or -not $resolved) {
        throw 'No se pudo validar el almacén privado; no se modificó ningún proceso.'
    }
    return [string]$resolved
}
