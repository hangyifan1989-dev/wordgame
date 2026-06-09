Write-Host "=== WordGame APK Builder ===" -ForegroundColor Cyan
Write-Host "Please restart PC if WSL2 was just installed" -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

Write-Host ""
Write-Host "[1/3] Starting Docker Desktop..." -ForegroundColor Green
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (-not (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Start-Process $dockerPath
    Write-Host "  Waiting for Docker (60s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 60
}

$env:Path += ";C:\Program Files\Docker\Docker\resources\bin"
$test = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Docker not ready, waiting more..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

Write-Host ""
Write-Host "[2/3] Pulling buildozer image and building APK..." -ForegroundColor Green
Write-Host "  First build downloads Android SDK/NDK (~1-2GB)" -ForegroundColor Yellow
Write-Host "  Expected time: 15-30 minutes" -ForegroundColor Yellow
Write-Host ""

docker run --interactive --tty --rm `
  --volume "${PWD}:/home/user/hostcwd" `
  --volume "$env:USERPROFILE\.buildozer:/home/user/.buildozer" `
  kivy/buildozer:2.3 `
  android debug

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[3/3] Build successful!" -ForegroundColor Green
    Write-Host "  APK in: $scriptDir\bin\" -ForegroundColor Cyan
    Get-ChildItem -Path "$scriptDir\bin" -Filter "*.apk" | ForEach-Object {
        Write-Host "  -> $($_.Name)" -ForegroundColor White
    }
} else {
    Write-Host ""
    Write-Host "Build failed, check network or retry" -ForegroundColor Red
}

Read-Host "Press Enter to exit"

