Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Starting ZuDoc eKYC Platform via Docker..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Check if docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker CLI not found. Please ensure Docker is installed and in your PATH." -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit"
    exit 1
}

# Check if Docker daemon is running
Write-Host "Checking Docker daemon status..." -ForegroundColor Yellow
$dockerRunning = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerRunning = $true
    }
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host "Docker daemon is not running! Attempting to launch Docker Desktop..." -ForegroundColor Yellow
    if (Test-Path "C:\Program Files\Docker\Docker\Docker Desktop.exe") {
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        Write-Host "Waiting for Docker Desktop to start (this may take 20-30 seconds)..." -ForegroundColor Yellow
        $retries = 0
        while ($retries -lt 15) {
            Start-Sleep -Seconds 3
            try {
                $null = docker info 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $dockerRunning = $true
                    break
                }
            } catch {}
            $retries++
            Write-Host "." -NoNewline
        }
        Write-Host ""
    }
}

if (-not $dockerRunning) {
    Write-Host "Please start Docker Desktop manually from the Start Menu, wait until it finishes starting, and run this script again." -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit"
    exit 1
}

# Auto-detect NVIDIA GPU availability for Docker
$hasGpu = $false
try {
    $null = docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) {
        $hasGpu = $true
    }
} catch {
    $hasGpu = $false
}

if ($hasGpu) {
    Write-Host "[HARDWARE] NVIDIA GPU detected & supported by Docker! Launching with RTX GPU Acceleration..." -ForegroundColor Green
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
} else {
    Write-Host "[HARDWARE] No NVIDIA GPU runtime found in Docker. Running safely in Portable CPU Mode..." -ForegroundColor Yellow
    docker compose -f docker-compose.yml up -d --build
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Docker containers are up! Access URLs:" -ForegroundColor Cyan
Write-Host "-------------------------------------------------" -ForegroundColor Cyan
Write-Host "Doctor Verification Portal (Nginx) : http://localhost:8081" -ForegroundColor Green
Write-Host "B2B Portal (Nginx)                 : http://localhost:8082" -ForegroundColor Green
Write-Host "Customer Portal / Verifyyy (Nginx) : http://localhost:8084" -ForegroundColor Green
Write-Host "Super Admin Dashboard              : http://localhost:5173" -ForegroundColor Green
Write-Host "Direct Backend API & Swagger Docs  : http://localhost:8085/docs" -ForegroundColor Yellow
Write-Host "OCR Engine Microservice            : http://localhost:5001" -ForegroundColor Yellow
Write-Host "RabbitMQ Management Console        : http://localhost:15672 (user: guest, pass: guest)" -ForegroundColor Yellow
Write-Host "PostgreSQL Database                : localhost:5433" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run 'docker compose ps' to see container health."
Write-Host "Run 'docker compose down' to stop all containers."
Write-Host ""
Read-Host -Prompt "Press Enter to exit"
