@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
if errorlevel 1 exit /b 1
echo Instalacion lista. Para una base nueva: .venv\Scripts\python.exe bootstrap_admin.py
echo La interfaz de web ya esta compilada. No se creo ni modifico ninguna cuenta.
pause
