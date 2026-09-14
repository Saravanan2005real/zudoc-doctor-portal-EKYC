@echo off
echo =================================================
echo Starting ZuDoc eKYC Platform via Docker...
echo =================================================

docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Docker daemon is not running!
    echo Attempting to start Docker Desktop...
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        echo Waiting for Docker daemon to initialize...
        timeout /t 20 /nobreak >nul
    )
)

docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker is still not running.
    echo Please start Docker Desktop from your Start Menu, wait until it is ready, and run this script again.
    pause
    exit /b 1
)

echo Building and starting Docker containers...
docker compose up -d --build

echo.
echo =================================================
echo All Docker containers are up! Access URLs:
echo -------------------------------------------------
echo Doctor Verification Portal (Nginx) : http://localhost:8081
echo B2B Portal (Nginx)                 : http://localhost:8082
echo Customer Portal / Verifyyy (Nginx) : http://localhost:8084
echo Super Admin Dashboard              : http://localhost:5173
echo Direct Backend API & Swagger Docs  : http://localhost:8085/docs
echo OCR Engine Microservice            : http://localhost:5001
echo RabbitMQ Management Console        : http://localhost:15672
echo PostgreSQL Database                : localhost:5433
echo =================================================
echo.
echo To view logs:  docker compose logs -f
echo To stop:       docker compose down
echo.
pause
