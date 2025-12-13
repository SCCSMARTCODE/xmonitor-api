# Run script for FastAPI application
Write-Host "Starting FastAPI Application..." -ForegroundColor Green

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Virtual environment not activated. Activating..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# Run the application
Write-Host "Running application on http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
python main.py

