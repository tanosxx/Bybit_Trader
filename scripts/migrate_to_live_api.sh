#!/bin/bash
# Автоматическая миграция на Gemini Live API

echo "🚀 Миграция на Gemini Live API (WebSockets)"
echo "=========================================="

# 1. Установка библиотеки
echo ""
echo "📦 Установка google-genai..."
docker exec bybit_bot pip install google-genai==0.2.2

# 2. Тест Live API
echo ""
echo "🧪 Тест Live API..."
docker exec bybit_bot python scripts/test_live_api.py

# 3. Обновление real_trader.py
echo ""
echo "🔄 Обновление real_trader.py..."
docker exec bybit_bot sed -i 's/from core.ai_brain import get_ai_brain/from core.ai_brain_live import get_ai_brain_live/g' /app/core/real_trader.py
docker exec bybit_bot sed -i 's/get_ai_brain()/get_ai_brain_live()/g' /app/core/real_trader.py

# 4. Перезапуск бота
echo ""
echo "🔄 Перезапуск бота..."
docker-compose restart bybit_bot

# 5. Проверка логов
echo ""
echo "📊 Проверка логов (Ctrl+C для выхода)..."
sleep 3
docker logs -f bybit_bot | grep -E "Live API|Подключено|🔌"
