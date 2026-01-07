#!/bin/bash
# Скрипт для проверки торгов после фикса Futures Brain

echo "=========================================="
echo "🔍 ПРОВЕРКА ТОРГОВ ПОСЛЕ ФИКСА"
echo "=========================================="
echo ""

# 1. Проверяем что контейнер работает
echo "1️⃣ Статус контейнера:"
docker ps | grep bybit_bot

echo ""
echo "2️⃣ Последние 30 строк логов (ищем сигналы):"
docker logs bybit_bot --tail 30 | grep -E "(FUTURES BRAIN|Score:|Raw Conf:|Trading Conf:|GATEKEEPER|Position opened|Position closed)"

echo ""
echo "3️⃣ Проверяем торги в БД (последние 10):"
docker exec -it bybit_postgres psql -U bybit_user -d bybit_db -c "
SELECT 
    id,
    symbol,
    side,
    entry_price,
    exit_price,
    pnl_usdt,
    win,
    closed_at
FROM trades_futures 
WHERE closed_at IS NOT NULL 
ORDER BY closed_at DESC 
LIMIT 10;
"

echo ""
echo "4️⃣ Статистика торгов за последние 24 часа:"
docker exec -it bybit_postgres psql -U bybit_user -d bybit_db -c "
SELECT 
    COUNT(*) as total_trades,
    SUM(CASE WHEN win = true THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN win = false THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN win = true THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric * 100, 2) as win_rate_pct,
    ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl,
    ROUND(AVG(pnl_usdt)::numeric, 2) as avg_pnl
FROM trades_futures 
WHERE closed_at > NOW() - INTERVAL '24 hours';
"

echo ""
echo "5️⃣ Открытые позиции:"
docker exec -it bybit_postgres psql -U bybit_user -d bybit_db -c "
SELECT 
    symbol,
    side,
    entry_price,
    quantity,
    leverage,
    opened_at
FROM trades_futures 
WHERE closed_at IS NULL;
"

echo ""
echo "=========================================="
echo "✅ Проверка завершена"
echo "=========================================="
