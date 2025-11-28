@echo off
echo ========================================
echo  DEPLOY BYBIT TRADER V2.0 TO SERVER
echo ========================================
echo.

set SERVER=root@88.210.10.145
set REMOTE_PATH=/root/Bybit_Trader

echo [1/5] Uploading core modules...
scp core\ta_lib.py %SERVER%:%REMOTE_PATH%/core/
scp core\backtester.py %SERVER%:%REMOTE_PATH%/core/
scp core\multi_agent.py %SERVER%:%REMOTE_PATH%/core/
scp core\loop.py %SERVER%:%REMOTE_PATH%/core/
scp core\real_trader.py %SERVER%:%REMOTE_PATH%/core/
scp core\spot_position_manager.py %SERVER%:%REMOTE_PATH%/core/

echo [2/5] Uploading web files...
scp web\app.py %SERVER%:%REMOTE_PATH%/web/
scp web\templates\dashboard_v2.html %SERVER%:%REMOTE_PATH%/web/templates/

echo [3/5] Uploading scripts...
scp scripts\run_backtest.py %SERVER%:%REMOTE_PATH%/scripts/

echo [4/5] Uploading memory-bank...
scp memory-bank\activeContext.md %SERVER%:%REMOTE_PATH%/memory-bank/
scp memory-bank\progress.md %SERVER%:%REMOTE_PATH%/memory-bank/

echo [5/5] Restarting Docker containers...
ssh %SERVER% "cd %REMOTE_PATH% && docker-compose restart"

echo.
echo ========================================
echo  DEPLOY COMPLETE!
echo ========================================
echo.
echo Dashboard: http://88.210.10.145:8585
echo.
pause
