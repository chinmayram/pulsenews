Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   PulseNews Multi-Source Aggregator & Dashboard" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python is not installed or not in PATH! Please install Python 3.10+." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "Checking requirements..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "Starting PulseNews Server..." -ForegroundColor Green
python main.py
