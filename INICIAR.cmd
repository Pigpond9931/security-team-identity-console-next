@echo off
setlocal
cd /d "%~dp0"
title SECURITY TEAM - Identity Console
if not exist ".venv\Scripts\python.exe" (
    echo Falta el entorno de Python. Consulta LEEME.md.
    pause
    exit /b 1
)
echo Identity Console - Windows
echo Abre http://127.0.0.1:8876
echo Para detener: Ctrl+C
".venv\Scripts\python.exe" "%~dp0server.py" --open
if errorlevel 1 pause
