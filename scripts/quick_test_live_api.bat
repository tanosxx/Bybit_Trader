@echo off
REM Быстрый тест Live API на сервере (не мешает обучению)

echo 🚀 Быстрый тест Gemini Live API
echo ================================

REM 1. Копируем файлы на сервер
echo.
echo 📤 Копирование файлов на сервер...
scp core/ai_brain_live.py root@88.210.10.145:/root/Bybit_Trader/core/
scp scripts/test_live_api.py root@88.210.10.145:/root/Bybit_Trader/scripts/

REM 2. Устанавливаем библиотеку
echo.
echo 📦 Установка google-genai на сервере...
ssh root@88.210.10.145 "docker exec bybit_bot pip install google-genai"

REM 3. Запускаем тест (не мешает обучению!)
echo.
echo 🧪 Запуск теста Live API...
ssh root@88.210.10.145 "docker exec bybit_bot python scripts/test_live_api.py"

echo.
echo ✅ Тест завершен!
pause
