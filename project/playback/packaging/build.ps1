$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Course Playback Assistant - Build Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$playbackDir = $projectRoot
Set-Location $playbackDir

Write-Host "[1/5] Checking Python environment..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK: Python version: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python was not found. Please install Python and add it to PATH." -ForegroundColor Red
    exit 1
}

Write-Host "[2/5] Checking dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Dependency installation failed" -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Dependencies installed/updated" -ForegroundColor Green

Write-Host "[3/6] Checking Playwright availability..." -ForegroundColor Yellow
try {
    $null = python -m playwright install --help 2>&1
    Write-Host "  OK: Playwright is available" -ForegroundColor Green
    Write-Host "  NOTE: First run may require: python -m playwright install chromium" -ForegroundColor Yellow
} catch {
    Write-Host "  WARNING: Playwright check warning: $_" -ForegroundColor Yellow
}

Write-Host "[4/6] Checking obsolete stdlib backports..." -ForegroundColor Yellow
$obsoleteBackports = @("typing", "pathlib")
$installedPackagesJson = python -m pip list --format=json 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($installedPackagesJson)) {
    Write-Host "  ERROR: Failed to query installed packages" -ForegroundColor Red
    exit 1
}
$installedPackages = $installedPackagesJson | ConvertFrom-Json
$installedNames = @($installedPackages | ForEach-Object { $_.name.ToLowerInvariant() })

foreach ($pkg in $obsoleteBackports) {
    if ($installedNames -contains $pkg) {
        Write-Host "  WARNING: Obsolete package '$pkg' found. Uninstalling..." -ForegroundColor Yellow
        python -m pip uninstall -y $pkg *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ERROR: Failed to uninstall obsolete package '$pkg'" -ForegroundColor Red
            exit 1
        }
        Write-Host "  OK: Removed obsolete '$pkg' package" -ForegroundColor Green
    } else {
        Write-Host "  OK: No obsolete '$pkg' package found" -ForegroundColor Green
    }
}

Write-Host "[5/6] Cleaning previous build artifacts..." -ForegroundColor Yellow
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "  OK: Removed dist directory" -ForegroundColor Green
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "  OK: Removed build directory" -ForegroundColor Green
}

Write-Host "[6/6] Building executable..." -ForegroundColor Yellow
$pyinstallerArgs = @(
    "gui.py",
    "--name", "Assistant",
    "--windowed",
    "--onefile",
    "--icon", "NONE",
    "--add-data", "engine.py;.",
    "--add-data", "video_detector.py;.",
    "--add-data", "utils.py;.",
    "--add-data", "main.py;.",
    "--hidden-import", "playwright",
    "--hidden-import", "playwright.async_api",
    "--hidden-import", "asyncio",
    "--hidden-import", "json",
    "--hidden-import", "logging",
    "--hidden-import", "time",
    "--clean",
    "--noconfirm"
)

pyinstaller $pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Build finished" -ForegroundColor Green

Write-Host ""
Write-Host "[Post] Preparing output files..." -ForegroundColor Yellow
$outputDir = "dist\Assistant"
if (!(Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$readmeContent = @"
Course Playback Assistant v1.0.0
==================

Quick Start:
1. Double-click "Assistant.exe"
2. Select a recorded JSON script in the GUI
3. Configure run parameters (or keep defaults)
4. Click "Start Playback"
5. If manual login is needed, complete login in browser and continue in GUI

First Run Notes:
- Ensure Microsoft Edge is installed
- Browser components may need to be installed once
  Command: python -m playwright install chromium

Config:
- You can save/load config for reuse
- Default config file name: gui_config.json

Logs:
- Runtime logs are shown in the bottom panel
- Logs can be exported for troubleshooting

Support:
- Record scripts using the companion browser extension
- Extension folder: project/extension
"@

$readmeContent | Out-File -FilePath "$outputDir\README.txt" -Encoding UTF8
Write-Host "  OK: README generated" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
$distDir = Join-Path $playbackDir "dist"
$exePath = Join-Path $distDir "Assistant.exe"
if (!(Test-Path $exePath)) {
    Write-Host ("ERROR: Executable not found: " + $exePath) -ForegroundColor Red
    Write-Host "Tip: check PyInstaller output above for actual errors." -ForegroundColor Yellow
    exit 1
}
Write-Host ("Output executable: " + $exePath) -ForegroundColor Cyan
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  1. Copy dist\Assistant.exe to any target location" -ForegroundColor White
Write-Host "  2. Double-click to launch" -ForegroundColor White
Write-Host ""
Write-Host 'Note: Please ensure Microsoft Edge is installed on the target machine' -ForegroundColor Yellow
Write-Host ""

$openDir = Read-Host "Open output directory now? (y/n)"
if ($openDir -eq "y" -or $openDir -eq "Y") {
    Start-Process explorer.exe -ArgumentList $distDir
}
