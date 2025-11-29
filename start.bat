@echo off
echo ================================
echo AI Hedge Fund System Launcher
echo ================================
echo.

REM 環境変数ファイルの確認
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure your API keys.
    pause
    exit /b 1
)

echo [1/4] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not running.
    echo Please install Docker Desktop and start it.
    pause
    exit /b 1
)

echo [2/4] Stopping existing containers...
docker-compose down

echo [3/4] Building and starting containers...
docker-compose up --build -d

echo [4/4] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ================================
echo System is ready!
echo ================================
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo.
pause
