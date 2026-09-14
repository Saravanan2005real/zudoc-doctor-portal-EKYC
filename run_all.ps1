Write-Host "Starting ZuDoc eKYC Platform..."

Write-Host "Starting Python Backend (Main Portal, API, OCR)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend_api; .\venv\Scripts\python.exe main.py"

Write-Host "Starting B2B Portal on port 8082..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd b2b_portal; python -m http.server 8082"

Write-Host "Starting Customer Portal on port 8084..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd customer_portal; python -m http.server 8084"

Write-Host "Starting Super Admin Dashboard..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd src\superadmin; npm run dev"

Write-Host "Starting Accessibility Frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd accessibility_frontend; npm run dev -- --port 5174"

Write-Host ""
Write-Host "================================================="
Write-Host "All services started! Here are your local links:"
Write-Host "-------------------------------------------------"
Write-Host "Main Backend (API, MedTrust UI, OCR) : http://localhost:8080"
Write-Host "B2B Portal                           : http://localhost:8082"
Write-Host "Customer Portal (Verifyyy)           : http://localhost:8084"
Write-Host "Super Admin Dashboard                : http://localhost:5173"
Write-Host "Accessibility Frontend               : http://localhost:5174"
Write-Host "================================================="
Write-Host ""
Read-Host -Prompt "Press Enter to exit"
