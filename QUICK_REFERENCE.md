# Quick Reference - Bybit Trading Bot

## 🚀 Быстрые команды

### Проверка статуса
```bash
# Все контейнеры
ssh root@88.210.10.145 "docker ps --filter name=bybit"

# Логи бота
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50"

# Баланс
ssh root@88.210.10.145 "docker exec bybit_db psql -U bybit_user -d bybit_trader -c \"SELECT 100.0 + SUM(pnl) - SUM(fee_entry + fee_exit) as balance FROM trades WHERE status = 'CLOSED' AND market_type = 'futures';\""

# Открытые позиции
ssh root@88.210.10.145 "docker exec bybit_db psql -U bybit_user -d bybit_trader -c \"SELECT symbol, side, entry_price, quantity FROM trades WHERE status = 'OPEN' AND market_type = 'futures';\""

# Strategic Regime
ssh root@88.210.10.145 "docker logs bybit_bot | grep 'Strategic Regime' | tail -5"
```

### Deployment (обычный)
```bash
# 1. Копируем файл
scp Bybit_Trader/core/file.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем (быстро, только изменённый слой)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# 3. Перезапускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Deployment (полная пересборка)
```bash
# Если что-то сломалось или изменили config.py
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Dashboard
```bash
# Пересборка dashboard
scp Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build dashboard"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d dashboard"

# Проверка API
ssh root@88.210.10.145 "curl -s http://localhost:8585/api/futures/positions"
ssh root@88.210.10.145 "curl -s http://localhost:8585/api/data | python3 -c \"import sys, json; d=json.load(sys.stdin); print('Balance:', d['futures_balance']['current_balance'])\""
```

## 📊 URLs

- **Dashboard:** http://88.210.10.145:8585
- **Neural HUD:** http://88.210.10.145:8585/brain
- **Futures Dashboard:** http://88.210.10.145:8585/futures

## 🔑 Ключевые файлы

### Конфигурация
- `config.py` - Основная конфигурация (баланс, риски, пары)
- `.env` - API ключи (НЕ коммитить!)
- `docker-compose.yml` - Docker сервисы

### Торговая логика
- `core/hybrid_loop.py` - Главный цикл
- `core/strategic_brain.py` - Strategic Brain (Gemini)
- `core/strategic_compliance.py` - Автоматическое закрытие позиций
- `core/ai_brain_local.py` - AI Brain (7 уровней фильтрации)
- `core/futures_brain.py` - Futures Brain (Multi-Agent)

### Dashboard
- `web/app.py` - Flask API
- `web/templates/brain.html` - Neural HUD
- `web/templates/dashboard_futures.html` - Futures Dashboard

### State Management
- `core/state.py` - GlobalBrainState (для Neural HUD)
- `ml_data/brain_state.json` - Shared state между контейнерами

## 🐛 Troubleshooting

### Бот не торгует (все SKIP)
```bash
# Проверить режим
ssh root@88.210.10.145 "docker logs bybit_bot | grep 'Strategic Regime' | tail -1"

# Если UNCERTAIN - это нормально, ждать 30 минут
# Если CHOP > 60 - ждать трендового движения
```

### Dashboard показывает старые данные
```bash
# Hard refresh в браузере: Ctrl+Shift+R

# Проверить что API работает
ssh root@88.210.10.145 "curl -s http://localhost:8585/api/data | python3 -m json.tool | head -20"
```

### Фантомные позиции
```bash
# Проверить БД (source of truth)
ssh root@88.210.10.145 "docker exec bybit_db psql -U bybit_user -d bybit_trader -c \"SELECT COUNT(*) FROM trades WHERE status = 'OPEN' AND market_type = 'futures';\""

# Должно совпадать с Dashboard
```

### Pydantic ValidationError
```bash
# Проверить .env
ssh root@88.210.10.145 "cat /root/Bybit_Trader/.env | grep -v 'API_KEY\|SECRET'"

# Добавить недостающую переменную
ssh root@88.210.10.145 "echo 'MISSING_VAR=dummy' >> /root/Bybit_Trader/.env"

# Пересобрать
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
```

## 📈 Мониторинг

### Ключевые метрики
- **Balance:** $111.31 (стартовый $100)
- **Win Rate:** 40% (цель: >30%)
- **Open Positions:** 0 (макс: 5)
- **Strategic Regime:** UNCERTAIN/SIDEWAYS/BULL_RUSH/BEAR_CRASH

### Проверка здоровья
```bash
# Все системы
ssh root@88.210.10.145 "curl -s http://localhost:8585/api/system/status | python3 -m json.tool"

# ML статус
ssh root@88.210.10.145 "curl -s http://localhost:8585/api/ml/status | python3 -m json.tool"

# Последние сделки
ssh root@88.210.10.145 "docker exec bybit_db psql -U bybit_user -d bybit_trader -c \"SELECT symbol, side, pnl, exit_time FROM trades WHERE status = 'CLOSED' AND market_type = 'futures' ORDER BY exit_time DESC LIMIT 5;\""

# Проверка RSS (должно быть пусто - нет предупреждений)
ssh root@88.210.10.145 "docker logs bybit_bot 2>&1 | grep -i rss"
```

## 🔧 Maintenance

### Очистка Docker
```bash
# Удалить неиспользуемые образы
ssh root@88.210.10.145 "docker image prune -a -f"

# Удалить неиспользуемые volumes
ssh root@88.210.10.145 "docker volume prune -f"

# Проверить размер
ssh root@88.210.10.145 "docker system df"
```

### Backup БД
```bash
# Экспорт trades
ssh root@88.210.10.145 "docker exec bybit_db pg_dump -U bybit_user -d bybit_trader -t trades > /tmp/trades_backup.sql"

# Скачать
scp root@88.210.10.145:/tmp/trades_backup.sql ./
```

### Restart всех сервисов
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose restart"
```

## 🆕 Последние изменения

### 5 декабря 2025, 16:30 UTC
- ✅ **RSS Fix:** Исправлены предупреждения RSS парсинга (syntax error, not well-formed)
- ✅ **Strategic Compliance:** Автоматическое закрытие позиций при смене режима
- ✅ **Docker Optimization:** Раздельные слои, .dockerignore, быстрая пересборка
- ✅ **Dashboard Fix:** Данные из БД вместо биржи (нет фантомных позиций)
- ✅ **Neural HUD v2:** AI Reasoning + Decision Flow + News Analysis

---
**Last Updated:** 2025-12-05 16:30 UTC
