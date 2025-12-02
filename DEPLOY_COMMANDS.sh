#!/bin/bash
# Деплой: Учёт виртуального баланса с комиссиями
# Дата: 2 декабря 2025

echo "🚀 Начинаем деплой изменений на сервер..."
echo ""

# Переходим в директорию проекта
cd "$(dirname "$0")"

echo "📦 Копируем файлы на сервер 88.210.10.145..."
echo ""

# 1. Новый файл balance_tracker.py
echo "1/4 Копируем balance_tracker.py..."
scp ./database/balance_tracker.py root@88.210.10.145:/root/Bybit_Trader/database/

# 2. Обновлённый futures_executor.py
echo "2/4 Копируем futures_executor.py..."
scp ./core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/

# 3. Обновлённый app.py
echo "3/4 Копируем app.py..."
scp ./web/app.py root@88.210.10.145:/root/Bybit_Trader/web/

# 4. Обновлённый dashboard_futures.html
echo "4/4 Копируем dashboard_futures.html..."
scp ./web/templates/dashboard_futures.html root@88.210.10.145:/root/Bybit_Trader/web/templates/

echo ""
echo "✅ Файлы скопированы!"
echo ""
echo "⚠️  Теперь выполни на сервере:"
echo ""
echo "ssh root@88.210.10.145"
echo "cd /root/Bybit_Trader"
echo "docker-compose down && docker-compose up -d --build"
echo "docker logs -f bybit_bot"
echo ""
