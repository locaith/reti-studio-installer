<#
    Build script for RETI Studio.

    1. Installs build/runtime deps (PyInstaller, pywebview) into the project venv.
    2. Ensures the bundled ffmpeg binary is present.
    3. Freezes the app with PyInstaller (one-folder) -> dist\RETI Studio\
    4. If Inno Setup (ISCC) is found, compiles the installer -> dist\installer\

    Usage (from anywhere):
        powershell -ExecutionPolicy Bypass -File packaging\build.ps1
#>
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan

$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
Write-Host "Python: $Py"

Write-Host "`n[1/4] Installing build dependencies..." -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
& $Py -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
& $Py -m pip install -r (Join-Path $ProjectRoot "requirements-build.txt")

Write-Host "`n[2/4] Ensuring bundled ffmpeg..." -ForegroundColor Cyan
$VendorFfmpeg = Join-Path $ProjectRoot "vendor\ffmpeg\ffmpeg.exe"
if (-not (Test-Path $VendorFfmpeg)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $VendorFfmpeg) | Out-Null
    $src = & $Py -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
    Copy-Item $src $VendorFfmpeg -Force
    Write-Host "Copied ffmpeg from $src"
} else {
    Write-Host "ffmpeg already present."
}

Write-Host "`n[3/4] Building with PyInstaller..." -ForegroundColor Cyan
if (Test-Path (Join-Path $ProjectRoot "build")) { Remove-Item -Recurse -Force (Join-Path $ProjectRoot "build") }
if (Test-Path (Join-Path $ProjectRoot "dist\RETI Studio")) { Remove-Item -Recurse -Force (Join-Path $ProjectRoot "dist\RETI Studio") }
& $Py -m PyInstaller (Join-Path $ProjectRoot "packaging\reti_studio.spec") --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
Write-Host "PyInstaller output: dist\RETI Studio\" -ForegroundColor Green

Write-Host "`n[4/4] Building installer with Inno Setup..." -ForegroundColor Cyan
$Iscc = $null
foreach ($p in @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Microsoft\WinGet\Links\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)) { if (Test-Path $p) { $Iscc = $p; break } }
if (-not $Iscc) { $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue; if ($cmd) { $Iscc = $cmd.Source } }

if ($Iscc) {
    & $Iscc (Join-Path $ProjectRoot "packaging\installer\reti-studio.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed." }
    Write-Host "`nInstaller created in dist\installer\" -ForegroundColor Green
} else {
    Write-Host "Inno Setup (ISCC.exe) not found." -ForegroundColor Yellow
    Write-Host "Install it from https://jrsoftware.org/isdl.php (or: winget install JRSoftware.InnoSetup)," -ForegroundColor Yellow
    Write-Host "then run:  ISCC packaging\installer\reti-studio.iss" -ForegroundColor Yellow
}
Write-Host "`nDone." -ForegroundColor Green
