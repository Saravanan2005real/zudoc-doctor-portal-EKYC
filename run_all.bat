@echo off
echo Starting ZuDoc eKYC Platform...

echo Starting Python Backend (Main Portal, API, OCR)...
start "Backend API & Portal" cmd /k "cd backend_api && .\venv\Scripts\python.exe main.py"

echo Starting B2B Portal on port 8082...
start "B2B Portal" cmd /k "cd b2b_portal && python -m http.server 8082"

echo Starting Customer Portal on port 8084...
start "Customer Portal" cmd /k "cd customer_portal && python -m http.server 8084"

echo Starting Super Admin Dashboard...
start "Super Admin" cmd /k "cd src\superadmin && npm run dev"

echo Starting Accessibility Frontend...
start "Accessibility Frontend" cmd /k "cd accessibility_frontend && npm run dev -- --port 5174"

echo All services started! Check the separate console windows.
pause
