@echo off
echo ========================================
echo  DEPLOY LOCAL CORE ARCHITECTURE
echo ========================================
echo.

REM Настройки сервера
set SERVER=root@88.210.10.145
set REMOTE_PATH=/root/Bybit_Trader

echo [1/4] Uploading updated files to server...
scp -r core\news_brain.py %SERVER%:%REMOTE_PATH%/core/
scp -r core\ai_brain_local.py %SERVER%:%REMOTE_PATH%/core/
scp -r core\loop.py %SERVER%:%REMOTE_PATH%/core/
scp -r core\real_trader.py %SERVER%:%REMOTE_PATH%/core/
scp -r core\spot_position_manager.py %SERVER%:%REMOTE_PATH%/core/
scp -r config.py %SERVER%:%REMOTE_PATH%/
scp -r requirements.txt %SERVER%:%REMOTE_PATH%/
scp -r .env %SERVER%:%REMOTE_PATH%/

echo.
echo [2/4] Connecting to server and rebuilding...
ssh %SERVER% "cd %REMOTE_PATH% && docker-compose down"

echo.
echo [3/4] Rebuilding Docker image...
ssh %SERVER% "cd %REMOTE_PATH% && docker-compose build --no-cache"

echo.
echo [4/4] Starting containers...
ssh %SERVER% "cd %REMOTE_PATH% && docker-compose up -d"

echo.
echo ========================================
echo  DEPLOY COMPLETE!
echo ========================================
echo.
echo Check logs: ssh %SERVER% "cd %REMOTE_PATH% && docker-compose logs -f bot"
echo.
pause
