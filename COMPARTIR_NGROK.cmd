@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" "%~dp0share_ngrok.py"
pause
