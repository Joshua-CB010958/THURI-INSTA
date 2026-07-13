@echo off
REM Double-click me. .ps1 files can't be double-clicked (Windows opens them in
REM Notepad), so this wrapper runs bootstrap.ps1 properly.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"
pause
