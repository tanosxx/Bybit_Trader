@echo off
echo Uploading files to VPS server...

REM Upload modified bybit_api.py
scp Bybit_Trader/core/bybit_api.py root@88.210.10.145:/root/Bybit_Trader/core/

REM Upload test script
scp Bybit_Trader/scripts/test_historical_api.py root@88.210.10.145:/root/Bybit_Trader/scripts/

echo.
echo Files uploaded! Now restart Docker and run tests:
echo.
echo ssh root@88.210.10.145
echo cd /root/Bybit_Trader
echo docker-compose restart bot
echo docker exec bybit_bot python scripts/test_historical_api.py
echo.
pause
