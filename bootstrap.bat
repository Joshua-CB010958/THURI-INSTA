@echo off
REM Double-click me. This downloads the latest installer from GitHub and runs it,
REM so it always updates to the newest version before starting the app.
REM (.ps1 files can't be double-clicked - Windows opens them in Notepad - so this
REM  wrapper runs the PowerShell installer properly.)
cd /d "%~dp0"

echo ==> Getting the latest installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Joshua-CB010958/THURI-INSTA/main/bootstrap.ps1' -OutFile '%~dp0bootstrap.ps1' -UseBasicParsing } catch { Write-Host '==> Could not download the latest - using the local copy.' }"

if exist "%~dp0bootstrap.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"
) else (
    echo Could not find or download bootstrap.ps1. Check your internet connection.
)
pause
