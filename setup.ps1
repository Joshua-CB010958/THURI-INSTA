# One-time setup: installs Python if needed, creates a virtualenv, installs
# dependencies, and prepares .env.  Safe to re-run.
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Instagram Scraper setup"

# Returns a working python.exe path, or $null. The Microsoft Store ships a fake
# python.exe under WindowsApps that opens the Store instead of running, so every
# candidate has to actually print a version before we trust it.
function Find-Python {
    $candidates = @()

    $launcher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($launcher) { $candidates += ,@($launcher.Source, @("-3")) }

    foreach ($name in @("python", "python3")) {
        foreach ($cmd in @(Get-Command $name -All -ErrorAction SilentlyContinue)) {
            if ($cmd.Source -and $cmd.Source -notlike "*\WindowsApps\*") {
                $candidates += ,@($cmd.Source, @())
            }
        }
    }

    # Installed but not on PATH (very common).
    $globs = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe"
        "$env:ProgramFiles\Python3*\python.exe"
        "C:\Python3*\python.exe"
    )
    foreach ($g in $globs) {
        foreach ($hit in @(Get-ChildItem $g -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)) {
            $candidates += ,@($hit.FullName, @())
        }
    }

    foreach ($c in $candidates) {
        $exe, $pre = $c
        try {
            $out = & $exe @pre "--version" 2>&1
            if ("$out" -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 9) {
                return [pscustomobject]@{ Exe = $exe; Pre = $pre; Version = "$out".Trim() }
            }
        } catch { }
    }
    return $null
}

function Install-Python {
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        Write-Host "==> Python not found. Installing it with winget (this takes a few minutes)..."
        winget install --id Python.Python.3.12 --exact --source winget --scope user `
            --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) { return }
        Write-Host "   -> winget didn't succeed, falling back to the official installer."
    } else {
        Write-Host "==> Python not found and winget isn't available. Downloading the official installer..."
    }

    $url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
    $exe = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
    Write-Host "==> Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing
    Write-Host "==> Running the installer (a UAC prompt may appear - click Yes)"
    Start-Process -FilePath $exe -Wait -ArgumentList @(
        "/passive", "InstallAllUsers=0", "PrependPath=1", "Include_launcher=1", "Include_test=0"
    )
    Remove-Item $exe -ErrorAction SilentlyContinue
}

# 1. Find Python 3 - installing it first if it isn't there.
$py = Find-Python
if (-not $py) {
    Install-Python
    $py = Find-Python          # freshly installed: PATH isn't refreshed in this
                               # session, but the glob above finds it on disk.
    if (-not $py) {
        Write-Host ""
        Write-Host "!! Python still isn't showing up. Install it by hand from"
        Write-Host "   https://www.python.org/downloads/ - tick 'Add python.exe to PATH' -"
        Write-Host "   then close this window and run setup.ps1 again."
        exit 1
    }
}
Write-Host "==> Using $($py.Version)  [$($py.Exe)]"

# 2. Create the virtualenv if missing.
if (-not (Test-Path ".venv")) {
    Write-Host "==> Creating virtual environment (.venv)"
    & $py.Exe @($py.Pre) "-m" "venv" ".venv"
}

# 3. Install dependencies.
Write-Host "==> Installing dependencies"
& ".\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

# 4. Create .env from the template if it doesn't exist yet.
if (-not (Test-Path ".env")) {
    Write-Host "==> Creating .env from template"
    Copy-Item ".env.example" ".env"
    Write-Host "   -> Edit .env and add your GEMINI_API_KEY (https://aistudio.google.com/apikey)"
}

Write-Host ""
Write-Host "==> Setup complete."
Write-Host "    1. Put your Gemini key in .env (GEMINI_API_KEY=...)"
Write-Host "    2. Log into Instagram in your browser (Chrome/Edge/Firefox/Brave)"
Write-Host "    3. Start the app:   .\start.ps1"
