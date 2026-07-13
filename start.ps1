# Starts the Instagram Scraper web app and opens it in your browser.
# Usage:  powershell -ExecutionPolicy Bypass -File start.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Run setup automatically if the venv isn't there yet.
if (-not (Test-Path ".venv")) {
    Write-Host "==> First run - setting up..."
    & "$PSScriptRoot\setup.ps1"
}

if (-not $env:PORT) { $env:PORT = "5001" }
$URL = "http://127.0.0.1:$($env:PORT)"

# Open the browser shortly after the server starts. Prefer Chrome; fall back
# to the system default browser if Chrome isn't installed.
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    $chrome = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($chrome) { Start-Process $chrome $using:URL }
    else { Start-Process $using:URL }
} | Out-Null

Write-Host "==> Starting Instagram Scraper at $URL  (press Ctrl+C to stop)"
& ".\.venv\Scripts\python.exe" app.py
