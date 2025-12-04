#!/bin/bash
# Деплой исправлений дашборда на сервер
# Дата: 2025-12-04
# Задачи:
# 1. ML статистика не обновляется (добавлены no-cache заголовки)
# 2. Индикаторы статуса систем (зелёные/красные лампочки)

echo "🚀 Deploying Dashboard Fixes to Server..."
echo ""
echo "📋 Changes:"
echo "  ✅ Fixed ML stats caching (no-cache headers in /api/ml/status)"
echo "  ✅ Added system status indicators (6 systems)"
echo "  ✅ Fixed corrupted HTML file"
echo ""
echo "📁 Files to deploy:"
echo "  - web/app.py (ML status endpoint with no-cache)"
echo "  - web/templates/dashboard_futures.html (system status + ML updates)"
echo ""
echo "⚠️  ВАЖНО: Пароль вводится ВРУЧНУЮ!"
echo ""

# Копируем файлы на сервер
echo "1️⃣  Копирование файлов на сервер..."
scp Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/
scp Bybit_Trader/web/templates/dashboard_futures.html root@88.210.10.145:/root/Bybit_Trader/web/templates/

echo ""
echo "2️⃣  Перезапуск dashboard контейнера..."
echo "Выполните на сервере:"
echo ""
echo "ssh root@88.210.10.145"
echo "cd /root/Bybit_Trader"
echo "docker-compose restart dashboard"
echo "docker logs -f dashboard --tail 50"
echo ""
echo "3️⃣  Проверка:"
echo "  - Откройте дашборд: http://88.210.10.145:5000"
echo "  - Проверьте что ML samples обновляются"
echo "  - Проверьте что индикаторы систем показывают статус"
echo ""
echo "✅ Готово!"
