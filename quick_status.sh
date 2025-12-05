#!/bin/bash
# Quick Status Check - Bybit Trading Bot
# Быстрая проверка статуса без Python

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║         BYBIT TRADING BOT - QUICK STATUS CHECK                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Server: 88.210.10.145"
echo ""

# Docker Containers
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DOCKER CONTAINERS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker ps --filter name=bybit --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
echo ""

# Balance
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "BALANCE & TRADES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT 
    'Starting Balance' as metric, 
    '\$100.00' as value
UNION ALL
SELECT 
    'Current Balance',
    '\$' || ROUND((100.0 + COALESCE(SUM(pnl), 0) - COALESCE(SUM(fee_entry + fee_exit), 0))::numeric, 2)::text
FROM trades WHERE status = 'CLOSED' AND market_type = 'futures'
UNION ALL
SELECT 
    'Net PnL',
    '\$' || ROUND((COALESCE(SUM(pnl), 0) - COALESCE(SUM(fee_entry + fee_exit), 0))::numeric, 2)::text
FROM trades WHERE status = 'CLOSED' AND market_type = 'futures'
UNION ALL
SELECT 
    'Total Trades',
    COUNT(*)::text
FROM trades WHERE market_type = 'futures'
UNION ALL
SELECT 
    'Open Positions',
    COUNT(*)::text
FROM trades WHERE status = 'OPEN' AND market_type = 'futures'
UNION ALL
SELECT 
    'Win Rate',
    ROUND(
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::numeric / 
        NULLIF(SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END), 0) * 100, 
        1
    )::text || '%'
FROM trades WHERE market_type = 'futures';
" -t
echo ""

# Strategic Brain
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STRATEGIC BRAIN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs bybit_bot 2>&1 | grep "Strategic Regime" | tail -1
echo ""

# Recent Trades
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "LAST 5 TRADES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT 
    symbol,
    side,
    ROUND(entry_price::numeric, 2) as entry,
    ROUND(COALESCE(exit_price, 0)::numeric, 2) as exit,
    ROUND(COALESCE(pnl, 0)::numeric, 2) as pnl,
    status,
    TO_CHAR(COALESCE(exit_time, entry_time), 'MM-DD HH24:MI') as time
FROM trades 
WHERE market_type = 'futures'
ORDER BY COALESCE(exit_time, entry_time) DESC 
LIMIT 5;
" -t
echo ""

# Errors Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ERROR CHECK (last 10 minutes)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ERROR_COUNT=$(docker logs bybit_bot --since 10m 2>&1 | grep -E "(Error|❌|Exception)" | wc -l)
RSS_COUNT=$(docker logs bybit_bot --since 10m 2>&1 | grep -i "rss warning" | wc -l)

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✅ No errors in last 10 minutes"
else
    echo "⚠️  Found $ERROR_COUNT errors in last 10 minutes"
    docker logs bybit_bot --since 10m 2>&1 | grep -E "(Error|❌|Exception)" | tail -5
fi

if [ $RSS_COUNT -eq 0 ]; then
    echo "✅ No RSS warnings"
else
    echo "⚠️  Found $RSS_COUNT RSS warnings"
fi
echo ""

# URLs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "URLS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Dashboard:   http://88.210.10.145:8585"
echo "Neural HUD:  http://88.210.10.145:8585/brain"
echo "Futures:     http://88.210.10.145:8585/futures"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CONTAINER_COUNT=$(docker ps --filter name=bybit --format "{{.Names}}" | wc -l)
if [ $CONTAINER_COUNT -eq 5 ] && [ $ERROR_COUNT -eq 0 ]; then
    echo "✅ ALL SYSTEMS OPERATIONAL"
else
    echo "⚠️  SOME ISSUES DETECTED"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
