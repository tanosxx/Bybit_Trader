#!/bin/bash
# Neural HUD Deployment Script
# Автоматический деплой Neural HUD на сервер

set -e  # Exit on error

SERVER="root@88.210.10.145"
PROJECT_PATH="/root/Bybit_Trader"

echo "🚀 Starting Neural HUD deployment..."

# 1. Копируем новый файл - GlobalBrainState
echo "📦 Copying core/state.py..."
scp Bybit_Trader/core/state.py $SERVER:$PROJECT_PATH/core/

# 2. Копируем обновлённые модули
echo "📦 Copying updated modules..."
scp Bybit_Trader/core/strategic_brain.py $SERVER:$PROJECT_PATH/core/
scp Bybit_Trader/core/ai_brain_local.py $SERVER:$PROJECT_PATH/core/

# 3. Копируем Flask app
echo "📦 Copying web/app.py..."
scp Bybit_Trader/web/app.py $SERVER:$PROJECT_PATH/web/

# 4. Копируем HTML template
echo "📦 Copying brain.html template..."
scp Bybit_Trader/web/templates/brain.html $SERVER:$PROJECT_PATH/web/templates/

# 5. Останавливаем контейнеры
echo "🛑 Stopping containers..."
ssh $SERVER "cd $PROJECT_PATH && docker-compose stop bot dashboard"

# 6. Удаляем старые контейнеры (ОБЯЗАТЕЛЬНО!)
echo "🗑️  Removing old containers..."
ssh $SERVER "docker rm -f bybit_bot bybit_dashboard"

# 7. Пересобираем образы
echo "🔨 Building new images..."
ssh $SERVER "cd $PROJECT_PATH && docker-compose build bot dashboard"

# 8. Запускаем контейнеры
echo "▶️  Starting containers..."
ssh $SERVER "cd $PROJECT_PATH && docker-compose up -d bot dashboard"

# 9. Ждём запуска
echo "⏳ Waiting for containers to start..."
sleep 5

# 10. Проверяем статус
echo "✅ Checking container status..."
ssh $SERVER "docker ps | grep bybit"

# 11. Проверяем логи
echo "📋 Checking logs..."
echo ""
echo "=== BOT LOGS (last 20 lines) ==="
ssh $SERVER "docker logs bybit_bot --tail 20"
echo ""
echo "=== DASHBOARD LOGS (last 20 lines) ==="
ssh $SERVER "docker logs bybit_dashboard --tail 20"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Neural HUD URL: http://88.210.10.145:8585/brain"
echo "🔍 API Endpoint: http://88.210.10.145:8585/api/brain_live"
echo ""
echo "📊 To monitor logs:"
echo "   docker logs -f bybit_bot"
echo "   docker logs -f bybit_dashboard"
