# Windows bootstrap. Sets the project up (installing Python if needed) and starts
# the app. Nothing needs to be installed first - no Python, no git.
#
# If you ALREADY have the project folder: open it in PowerShell and run
#     .\bootstrap.ps1
# and it uses the files that are already there - it downloads nothing.
#
# From a bare machine, with no copy of the project at all:
#     iwr -useb https://raw.githubusercontent.com/Joshua-CB010958/THURI-INSTA/main/bootstrap.ps1 | iex
#
$ErrorActionPreference = "Stop"

$repo = "https://github.com/Joshua-CB010958/THURI-INSTA"
$raw  = "https://raw.githubusercontent.com/Joshua-CB010958/THURI-INSTA/main"

Write-Host "==> Instagram Scraper - Windows bootstrap"

# 1. Work out where the project is. Prefer a copy that already exists: the folder
#    we were run from, then the current directory, then the default location.
$project = $null
foreach ($dir in @($PSScriptRoot, (Get-Location).Path, (Join-Path $env:USERPROFILE "THURI-INSTA"))) {
    if ($dir -and (Test-Path (Join-Path $dir "app.py"))) { $project = $dir; break }
}

if ($project) {
    Write-Host "==> Using the copy already here: $project"
} else {
    # 2. No copy anywhere - fetch one.
    $project = Join-Path $env:USERPROFILE "THURI-INSTA"
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "==> Cloning into $project"
        git clone "$repo.git" $project
    } else {
        $zip = Join-Path $env:TEMP "thuri-insta.zip"
        $tmp = Join-Path $env:TEMP "thuri-insta-unzip"
        Write-Host "==> Downloading the project ZIP"
        Invoke-WebRequest -Uri "$repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing

        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
        Expand-Archive -Path $zip -DestinationPath $tmp -Force

        # GitHub ZIPs unpack into a single <repo>-<branch> folder.
        $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
        Write-Host "==> Unpacking to $project"
        Move-Item $inner.FullName $project
        Remove-Item $zip, $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
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
