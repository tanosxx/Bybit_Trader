#!/bin/bash
# Перезапуск бота после фикса

echo "🔄 Останавливаем старый контейнер..."
docker-compose stop bot
docker rm -f bybit_bot

echo ""
echo "🏗️ Пересобираем образ..."
docker-compose build --no-cache bot

echo ""
echo "🚀 Запускаем бота..."
docker-compose up -d bot

echo ""
echo "⏳ Ждём 5 секунд..."
sleep 5

echo ""
echo "📋 Последние 50 строк логов:"
docker logs bybit_bot --tail 50
