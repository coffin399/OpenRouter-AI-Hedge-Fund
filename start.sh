#!/bin/bash

echo "================================"
echo "AI Hedge Fund System Launcher"
echo "================================"
echo ""

# 環境変数ファイルの確認 (.env が無ければ .env.example から自動コピー)
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "[INFO] .env not found. Creating from .env.example ..."
        cp .env.example .env
    else
        echo "[ERROR] .env file not found!"
        echo "[ERROR] .env.example also missing. Please create .env manually."
        exit 1
    fi
fi

# Dockerの確認
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed."
    echo "Please install Docker and try again."
    exit 1
fi

echo "[1/4] Checking Docker..."
if ! docker info &> /dev/null; then
    echo "[ERROR] Docker daemon is not running."
    echo "Please start Docker and try again."
    exit 1
fi

echo "[2/4] Stopping existing containers..."
docker-compose down

echo "[3/4] Building and starting containers..."
docker-compose up --build -d

echo "[4/4] Waiting for services to be ready..."
sleep 10

echo ""
echo "================================"
echo "System is ready!"
echo "================================"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo ""
