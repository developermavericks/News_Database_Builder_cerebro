$ErrorActionPreference = "Stop"

$pythonExe = "python"
if (Test-Path "backend\venv\Scripts\python.exe") {
    $pythonExe = "backend\venv\Scripts\python.exe"
}

while ($true) {
    Write-Host "Booting NEXUS Launcher..." -ForegroundColor Cyan
    & $pythonExe "start.py"
    Write-Host "NEXUS Launcher exited or was terminated. Restarting in 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}
