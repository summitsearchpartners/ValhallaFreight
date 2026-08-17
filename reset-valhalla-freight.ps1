Write-Host "Resetting Valhalla Freight local database and containers..." -ForegroundColor Yellow
docker compose down -v
docker compose up --build
