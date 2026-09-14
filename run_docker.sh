#!/bin/bash
set -e

echo "================================================="
echo "Starting ZuDoc eKYC Platform via Docker..."
echo "================================================="

if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
    echo "[HARDWARE] NVIDIA GPU detected & supported by Docker! Launching with RTX GPU Acceleration..."
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
else
    echo "[HARDWARE] No NVIDIA GPU runtime found in Docker. Running safely in Portable CPU Mode..."
    docker compose -f docker-compose.yml up -d --build
fi

echo ""
echo "================================================="
echo "Docker containers are up! Access URLs:"
echo "-------------------------------------------------"
echo "Doctor Verification Portal (Nginx) : http://localhost:8081"
echo "B2B Portal (Nginx)                 : http://localhost:8082"
echo "Customer Portal / Verifyyy (Nginx) : http://localhost:8084"
echo "Super Admin Dashboard              : http://localhost:5173"
echo "Direct Backend API & Swagger Docs  : http://localhost:8085/docs"
echo "OCR Engine Microservice            : http://localhost:5001"
echo "================================================="
