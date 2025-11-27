@echo off
REM Автоматическая миграция на Gemini Live API (Windows)

echo 🚀 Миграция на Gemini Live API (WebSockets)
echo ==========================================

REM 1. Установка библиотеки
echo.
echo 📦 Установка google-genai...
docker exec bybit_bot pip install google-genai==0.2.2

REM 2. Тест Live API
echo.
echo 🧪 Тест Live API...
docker exec bybit_bot python scripts/test_live_api.py

REM 3. Обновление real_trader.py
echo.
echo 🔄 Обновление real_trader.py...
docker exec bybit_bot sed -i "s/from core.ai_brain import get_ai_brain/from core.ai_brain_live import get_ai_brain_live/g" /app/core/real_trader.py
docker exec bybit_bot sed -i "s/get_ai_brain()/get_ai_brain_live()/g" /app/core/real_trader.py

REM 4. Перезапуск бота
echo.
echo 🔄 Перезапуск бота...
docker-compose restart bybit_bot

REM 5. Проверка логов
echo.
echo 📊 Проверка логов (Ctrl+C для выхода)...
timeout /t 3 /nobreak >nul
docker logs -f bybit_bot

pause
