Write-Host "Restarting Valhalla Freight while preserving database and documents..." -ForegroundColor Yellow
docker compose up -d --build
