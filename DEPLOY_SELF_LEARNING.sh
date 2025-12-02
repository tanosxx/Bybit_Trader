#!/bin/bash
# Деплой Self-Learning Module
# Дата: 2025-12-02

echo "🧠 Deploying Self-Learning Module..."
echo ""

# Переходим в директорию проекта
cd "$(dirname "$0")"

echo "📦 Step 1: Copying files to server..."
echo ""

# 1. Новый модуль self_learning.py
echo "1/7 Copying self_learning.py..."
scp ./core/self_learning.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Обновлённый models.py
echo "2/7 Copying models.py..."
scp ./database/models.py root@88.210.10.145:/root/Bybit_Trader/database/

# 3. Обновлённый ai_brain_local.py
echo "3/7 Copying ai_brain_local.py..."
scp ./core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/

# 4. Обновлённый futures_executor.py
echo "4/7 Copying futures_executor.py..."
scp ./core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/

# 5. Обновлённый base_executor.py
echo "5/7 Copying base_executor.py..."
scp ./core/executors/base_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/

# 6. Обновлённый hybrid_loop.py
echo "6/7 Copying hybrid_loop.py..."
scp ./core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/

# 7. Обновлённый position_monitor.py
echo "7/7 Copying position_monitor.py..."
scp ./core/position_monitor.py root@88.210.10.145:/root/Bybit_Trader/core/

# 8. Миграция БД
echo "8/9 Copying DB migration..."
scp ./database/migrations/add_ml_features.sql root@88.210.10.145:/root/Bybit_Trader/database/migrations/

# 9. Requirements
echo "9/9 Copying requirements.txt..."
scp ./requirements.txt root@88.210.10.145:/root/Bybit_Trader/

echo ""
echo "✅ Files copied!"
echo ""
echo "⚠️  Now execute on server:"
echo ""
echo "ssh root@88.210.10.145"
echo ""
echo "# Step 1: Apply DB migration"
echo "cd /root/Bybit_Trader"
echo "docker exec -i bybit_db psql -U bybit_user -d bybit_trader < database/migrations/add_ml_features.sql"
echo ""
echo "# Step 2: Rebuild containers"
echo "docker-compose down"
echo "docker-compose up -d --build"
echo ""
echo "# Step 3: Check logs"
echo "docker logs -f bybit_bot | grep -E 'Self-Learning|🧠'"
echo ""
