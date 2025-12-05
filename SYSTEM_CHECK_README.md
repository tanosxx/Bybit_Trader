# System Check Scripts - Инструкция

## 📋 Доступные скрипты

### 1. `system_check.py` - Полная проверка (Python)
**Что проверяет:**
- ✅ Database connection и таблицы
- ✅ Balance и статистика сделок
- ✅ Strategic Brain (режим, кэш)
- ✅ ML Systems (LSTM, Self-Learning, Candles)
- ✅ News Brain (sentiment, headlines)
- ✅ Configuration (все настройки)
- ✅ Recent Activity (последние сделки и решения)

**Использование:**
```bash
# На сервере (внутри контейнера)
ssh root@88.210.10.145
docker exec -it bybit_bot python system_check.py

# Или напрямую
ssh root@88.210.10.145 "docker exec bybit_bot python system_check.py"
```

**Вывод:**
- Цветной терминал с эмодзи
- Детальная информация по каждой системе
- Итоговая сводка с ключевыми метриками

---

### 2. `quick_status.sh` - Быстрая проверка (Bash)
**Что проверяет:**
- ✅ Docker containers (статус)
- ✅ Balance (из БД)
- ✅ Strategic Brain (последний режим)
- ✅ Last 5 trades
- ✅ Errors в логах (последние 10 минут)
- ✅ RSS warnings

**Использование:**
```bash
# На сервере
ssh root@88.210.10.145
cd /root/Bybit_Trader
./quick_status.sh

# Или напрямую
ssh root@88.210.10.145 "cd /root/Bybit_Trader && ./quick_status.sh"
```

**Вывод:**
- Простой текстовый формат
- Быстрая проверка (2-3 секунды)
- Легко копировать в отчёты

---

## 🚀 Deployment

### Копирование на сервер
```bash
# Python скрипт
scp Bybit_Trader/system_check.py root@88.210.10.145:/root/Bybit_Trader/

# Bash скрипт
scp Bybit_Trader/quick_status.sh root@88.210.10.145:/root/Bybit_Trader/
ssh root@88.210.10.145 "chmod +x /root/Bybit_Trader/quick_status.sh"
```

---

## 📊 Примеры вывода

### system_check.py
```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           BYBIT TRADING BOT - SYSTEM CHECK REPORT                 ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

Date: 2025-12-05 16:30:00 UTC
Server: 88.210.10.145
Environment: Demo Trading (Bybit Testnet)

======================================================================
                           DATABASE CHECK                            
======================================================================

✅ Database Connection: OK PostgreSQL connected
✅ Table 'trades': OK 23 records
✅ Table 'candles': OK 62,582 records
✅ Table 'wallet_history': OK 150 records
✅ Table 'ai_decisions': OK 1,234 records
✅ Table 'system_logs': OK 5,678 records

======================================================================
                           BALANCE CHECK                             
======================================================================

✅ Starting Balance: OK $100.00
✅ Current Balance: OK $111.31
✅ Net PnL: OK +$11.31 (+11.31%)
✅ Gross PnL: OK +$12.78
✅ Total Fees: OK $1.47

✅ Total Trades: OK 23
✅ Closed Trades: OK 17
✅ Open Positions: OK 0
✅ Wins: OK 7
✅ Losses: OK 10
✅ Win Rate: OK 41.2%

... (и так далее)
```

### quick_status.sh
```
╔════════════════════════════════════════════════════════════════════╗
║         BYBIT TRADING BOT - QUICK STATUS CHECK                    ║
╚════════════════════════════════════════════════════════════════════╝

Date: 2025-12-05 16:30:00 UTC
Server: 88.210.10.145

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCKER CONTAINERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NAMES              STATUS              PORTS
bybit_bot          Up 2 hours          
bybit_dashboard    Up 2 hours          0.0.0.0:8585->5000/tcp
bybit_sync         Up 2 days           
bybit_monitor      Up 2 days           
bybit_db           Up 2 days           0.0.0.0:5435->5432/tcp

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BALANCE & TRADES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 metric            | value
-------------------+--------
 Starting Balance  | $100.00
 Current Balance   | $111.31
 Net PnL           | $11.31
 Total Trades      | 23
 Open Positions    | 0
 Win Rate          | 41.2%

... (и так далее)
```

---

## 🔧 Troubleshooting

### Ошибка: "Permission denied"
```bash
# Сделать скрипт исполняемым
ssh root@88.210.10.145 "chmod +x /root/Bybit_Trader/quick_status.sh"
```

### Ошибка: "Module not found" (system_check.py)
```bash
# Запускать внутри контейнера
docker exec -it bybit_bot python system_check.py
```

### Ошибка: "psql: command not found"
```bash
# Использовать docker exec для БД команд
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "SELECT 1"
```

---

## 📝 Когда использовать

### system_check.py (полная проверка)
- 🔍 После деплоя (проверить что всё работает)
- 🐛 При дебаге проблем
- 📊 Для детального отчёта
- 🧪 После изменения конфигурации

### quick_status.sh (быстрая проверка)
- ⚡ Ежедневная проверка
- 📋 Для копирования в отчёты
- 🚀 Перед деплоем (baseline)
- 👀 Мониторинг в течение дня

---

## 🎯 Автоматизация

### Cron job для ежедневной проверки
```bash
# Добавить в crontab на сервере
0 9 * * * cd /root/Bybit_Trader && ./quick_status.sh > /tmp/daily_status.txt 2>&1
```

### Telegram уведомления
```bash
# Отправить отчёт в Telegram
./quick_status.sh | curl -X POST \
  "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>" \
  -d "text=$(cat -)" \
  -d "parse_mode=HTML"
```

---

## 📚 Дополнительно

### Сохранение отчёта в файл
```bash
# Python скрипт
docker exec bybit_bot python system_check.py > system_report_$(date +%Y%m%d).txt

# Bash скрипт
./quick_status.sh > quick_status_$(date +%Y%m%d).txt
```

### Сравнение с предыдущим отчётом
```bash
# Сохранить baseline
./quick_status.sh > baseline.txt

# Позже сравнить
./quick_status.sh > current.txt
diff baseline.txt current.txt
```

---

**Создано:** 2025-12-05  
**Автор:** AI Assistant  
**Версия:** 1.0
