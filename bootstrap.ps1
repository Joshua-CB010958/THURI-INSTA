# Windows bootstrap. Sets the project up (installing Python if needed) and starts
# the app. Nothing needs to be installed first - no Python, no git.
#
# If you ALREADY have the project folder: open it in PowerShell and run
#     .\bootstrap.ps1
# and it uses the files that are already there - it downloads nothing.
#
# From a bare machine, with no copy of the project at all:
#     iwr -useb https://raw.githubusercontent.com/Joshua-CB010958/THURI-INSTA/main/bootstrap.ps1 | iex
# The project is installed into the folder this bootstrap file is in (or the
# current directory when run straight from the web).
#
$ErrorActionPreference = "Stop"

$repo = "https://github.com/Joshua-CB010958/THURI-INSTA"
$raw  = "https://raw.githubusercontent.com/Joshua-CB010958/THURI-INSTA/main"

Write-Host "==> Instagram Scraper - Windows bootstrap"

# 1. Work out where the project is. Prefer a copy that already exists: the folder
#    we were run from, then the current directory, then the old default location.
#    New installs go next to this bootstrap file (or the current directory when
#    run straight from the web, where there is no script file).
if ($PSScriptRoot) { $base = $PSScriptRoot } else { $base = (Get-Location).Path }

$project = $null
foreach ($dir in @($base, (Get-Location).Path, (Join-Path $env:USERPROFILE "THURI-INSTA"))) {
    if ($dir -and (Test-Path (Join-Path $dir "app.py"))) { $project = $dir; break }
}

if ($project) {
    Write-Host "==> Using the copy already here: $project"
} else {
    # 2. No copy anywhere - fetch one into $base. The folder may already hold
    #    this bootstrap file, so fetch to a temp folder and move the contents in,
    #    leaving any files that are already there alone.
    $project = $base
    $tmp = Join-Path $env:TEMP "thuri-insta-fetch"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "==> Cloning into $project"
        git clone "$repo.git" $tmp
        $inner = Get-Item $tmp
    } else {
        $zip = Join-Path $env:TEMP "thuri-insta.zip"
        Write-Host "==> Downloading the project ZIP"
        Invoke-WebRequest -Uri "$repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
        Expand-Archive -Path $zip -DestinationPath $tmp -Force

        # GitHub ZIPs unpack into a single <repo>-<branch> folder.
        $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
    }

    Write-Host "==> Unpacking to $project"
    foreach ($item in Get-ChildItem $inner.FullName -Force) {
        $dest = Join-Path $project $item.Name
        if (-not (Test-Path $dest)) { Move-Item $item.FullName $dest }
    }
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

# 3. An older copy of the project may predate the Windows scripts - fetch any
#    that are missing rather than making the user re-download the whole thing.
foreach ($f in @("setup.ps1", "start.ps1")) {
    $path = Join-Path $project $f
    if (-not (Test-Path $path)) {
        Write-Host "==> $f is missing from this copy - downloading it"
        Invoke-WebRequest -Uri "$raw/$f" -OutFile $path -UseBasicParsing
    }
}

Set-Location $project
Write-Host ""
& (Join-Path $project "setup.ps1")
Write-Host ""
& (Join-Path $project "start.ps1")
