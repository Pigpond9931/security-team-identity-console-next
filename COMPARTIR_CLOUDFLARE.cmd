@echo off
cd /d "%~dp0"
title SECURITY TEAM - Cloudflare
".venv\Scripts\python.exe" -u supervise_cloudflare.py --open
pause
