Write-Host "Resetting FreightForge local database and containers..." -ForegroundColor Yellow
docker compose down -v
docker compose up --build
