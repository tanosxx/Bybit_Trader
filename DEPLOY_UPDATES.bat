@echo off
REM Скрипт для деплоя обновлений на сервер (Windows)

set SERVER=root@88.210.10.145
set REMOTE_PATH=/root/Bybit_Trader

echo 🚀 Деплой обновлений Bybit Trading Bot...
echo.

REM 1. Копируем обновленные файлы
echo 📦 Копирование файлов на сервер...
scp config.py %SERVER%:%REMOTE_PATH%/
scp core/ai_brain.py %SERVER%:%REMOTE_PATH%/core/
scp web/dashboard.py %SERVER%:%REMOTE_PATH%/web/
scp .env.example %SERVER%:%REMOTE_PATH%/

echo ✅ Файлы скопированы
echo.

REM 2. Обновляем .env на сервере
echo ⚙️ Обновление .env на сервере...
ssh %SERVER% "cd /root/Bybit_Trader && grep -q 'GOOGLE_API_KEY_1' .env || echo 'GOOGLE_API_KEY_1=AIzaSyCalj1ugvpU1thqDtROGCEgIGdXDFBIOJM' >> .env"
ssh %SERVER% "cd /root/Bybit_Trader && grep -q 'GOOGLE_API_KEY_2' .env || echo 'GOOGLE_API_KEY_2=AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c' >> .env"
ssh %SERVER% "cd /root/Bybit_Trader && grep -q 'GOOGLE_API_KEY_3' .env || echo 'GOOGLE_API_KEY_3=AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c' >> .env"
ssh %SERVER% "cd /root/Bybit_Trader && grep -q 'BYBIT_BASE_URL' .env || echo 'BYBIT_BASE_URL=https://api-demo.bybit.com' >> .env"

echo ✅ .env обновлен
echo.

REM 3. Перезапускаем Docker
echo 🔄 Перезапуск Docker контейнеров...
ssh %SERVER% "cd /root/Bybit_Trader && docker-compose down && docker-compose up -d --build"

echo ✅ Docker перезапущен
echo.

REM 4. Проверяем статус
echo 📊 Проверка статуса...
timeout /t 5 /nobreak >nul
ssh %SERVER% "cd /root/Bybit_Trader && docker-compose ps"

echo.
echo ✅ Деплой завершен!
echo.
echo 🌐 Dashboard: http://88.210.10.145:8585
echo 📋 Логи: ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose logs -f"
echo.

pause
