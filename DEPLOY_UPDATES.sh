#!/bin/bash
# Скрипт для деплоя обновлений на сервер

SERVER="root@88.210.10.145"
REMOTE_PATH="/root/Bybit_Trader"

echo "🚀 Деплой обновлений Bybit Trading Bot..."
echo ""

# 1. Копируем обновленные файлы
echo "📦 Копирование файлов на сервер..."
scp config.py $SERVER:$REMOTE_PATH/
scp core/ai_brain.py $SERVER:$REMOTE_PATH/core/
scp web/dashboard.py $SERVER:$REMOTE_PATH/web/
scp .env.example $SERVER:$REMOTE_PATH/

echo "✅ Файлы скопированы"
echo ""

# 2. Обновляем .env на сервере
echo "⚙️ Обновление .env на сервере..."
ssh $SERVER << 'EOF'
cd /root/Bybit_Trader

# Проверяем наличие новых переменных
if ! grep -q "GOOGLE_API_KEY_1" .env; then
    echo "Добавляем Gemini ключи в .env..."
    echo "" >> .env
    echo "# AI APIs - Gemini (3 ключа для ротации)" >> .env
    echo "GOOGLE_API_KEY_1=AIzaSyCalj1ugvpU1thqDtROGCEgIGdXDFBIOJM" >> .env
    echo "GOOGLE_API_KEY_2=AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c" >> .env
    echo "GOOGLE_API_KEY_3=AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c" >> .env
fi

if ! grep -q "BYBIT_BASE_URL" .env; then
    echo "Добавляем BYBIT_BASE_URL в .env..."
    sed -i '/BYBIT_TESTNET/a BYBIT_BASE_URL=https://api-demo.bybit.com' .env
fi

# Удаляем старую переменную GOOGLE_API_KEY если есть
sed -i '/^GOOGLE_API_KEY=/d' .env

echo "✅ .env обновлен"
EOF

echo ""

# 3. Перезапускаем Docker
echo "🔄 Перезапуск Docker контейнеров..."
ssh $SERVER << 'EOF'
cd /root/Bybit_Trader
docker-compose down
docker-compose up -d --build
EOF

echo "✅ Docker перезапущен"
echo ""

# 4. Проверяем статус
echo "📊 Проверка статуса..."
sleep 5
ssh $SERVER << 'EOF'
cd /root/Bybit_Trader
docker-compose ps
EOF

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "🌐 Dashboard: http://88.210.10.145:8585"
echo "📋 Логи: ssh root@88.210.10.145 'cd /root/Bybit_Trader && docker-compose logs -f'"
echo ""
