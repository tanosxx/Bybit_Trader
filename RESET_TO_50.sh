#!/bin/bash
# Сброс системы на $50 баланс и очистка торговых данных

echo "=========================================="
echo "🔄 RESET TO $50 BALANCE"
echo "=========================================="
echo ""

# 1. Останавливаем бота
echo "1️⃣ Stopping bot..."
docker-compose stop bot

echo ""
echo "2️⃣ Clearing trading data (preserving ML data)..."
docker exec bybit_db psql -U bybit_user -d bybit_trader -f /tmp/reset_trading_data.sql

echo ""
echo "3️⃣ Rebuilding bot with new config..."
docker-compose build bot

echo ""
echo "4️⃣ Starting bot..."
docker-compose up -d bot

echo ""
echo "5️⃣ Waiting 10 seconds for initialization..."
sleep 10

echo ""
echo "6️⃣ Checking bot status..."
docker ps | grep bybit_bot

echo ""
echo "7️⃣ Last 50 lines of logs:"
docker logs bybit_bot --tail 50

echo ""
echo "=========================================="
echo "✅ RESET COMPLETE"
echo "=========================================="
echo ""
echo "📊 Verify:"
echo "   - Balance: \$50"
echo "   - Trades: 0"
echo "   - ML data: preserved"
echo ""
echo "🔍 Check logs: docker logs -f bybit_bot"
echo "🔍 Check DB: docker exec bybit_db psql -U bybit_user -d bybit_trader -c 'SELECT COUNT(*) FROM trades;'"
