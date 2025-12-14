# TELEGRAM COMMANDER v1.0 - Интерактивный командир бота
**Дата:** 12 декабря 2025, 01:40 UTC  
**Статус:** ✅ Готово к деплою

---

## 🎯 ФИЛОСОФИЯ "SILENT MODE"

Бот **МОЛЧИТ** по умолчанию. Никаких уведомлений о каждой сделке, TP/SL, funding rate и т.д.

**Бот пишет ТОЛЬКО в двух случаях:**
1. **На команду** - ты спросил, он ответил
2. **ЧП** - Safety Guardian сработал, ошибка API, риск ликвидации

---

## 📱 КОМАНДЫ

### `/start` - Приветствие
```
🤖 Bybit Trading Bot Commander

SILENT MODE - бот молчит по умолчанию

Доступные команды:
/status - Сводка одним взглядом
/brain - Что думает система
/balance - Детальный баланс
/panic - 🚨 Emergency Stop

Бот пишет только на команды или при ЧП
```

### `/status` - Сводка одним взглядом
```
📊 STATUS REPORT

💰 Balance: $379.10
🟢 PnL: +$279.10 (+279.0%)

📈 Positions: 3
   🟢 Long: 2
   🔴 Short: 1

🧠 Regime: SIDEWAYS
⏰ Time: 01:40:15 UTC
```

### `/brain` - Что думает система
```
🧠 BRAIN STATUS

Strategic Regime: SIDEWAYS
   Updated: 15m ago

Gatekeepers:
   🚦 CHOP Filter: Active
   📊 Pattern Filter: Active
   👑 BTC Correlation: Active
   💸 Funding Filter: Active

Safety:
   🛡️ Guardian: OK
   ⚠️ Panic Mode: OFF
```

### `/balance` - Детальный баланс
```
💰 BALANCE DETAILS

Virtual Balance:
   Initial: $100.00
   Current: $379.10
   Realized PnL: +$279.10
   ROI: +279.0%

Leverage: 5x
Buying Power: $1,895.50

⚠️ Demo Trading Mode
```

### `/panic` - 🚨 Emergency Stop
```
🚨 PANIC ACTIVATED

Closing all positions...

✅ PANIC COMPLETE

Closed positions: 3
Bot paused: YES

⚠️ Trading stopped. Restart bot to resume.
```

**Что делает:**
1. Закрывает ВСЕ открытые позиции
2. Активирует `panic_mode = True`
3. Останавливает торговлю (новые сигналы игнорируются)

**Как возобновить:**
Перезапустить контейнер: `docker-compose restart bot`

---

## 🚨 EMERGENCY NOTIFICATIONS

Бот автоматически пишет при ЧП:

### Safety Guardian сработал
```
🚨 SAFETY GUARDIAN ALERT

Position size exceeded: $850 > $800 limit
Symbol: BTCUSDT
Action: Position blocked
```

### Ошибка API
```
🚨 API ERROR

Bybit API unavailable
Error: Connection timeout
Retrying in 30s...
```

### Риск ликвидации
```
🚨 LIQUIDATION RISK

Margin ratio: 85%
Positions at risk: 2
Action: Reduce leverage immediately
```

---

## 🔧 ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Архитектура

**Класс:** `TelegramCommander`

**Singleton:** `get_telegram_commander(executor, ai_brain, strategic_brain)`

**Работа:**
- Асинхронный (не блокирует основной цикл торговли)
- Polling mode (проверяет сообщения каждые 2 секунды)
- Проверка админа (только `TELEGRAM_CHAT_ID` может писать)

### Интеграция в `hybrid_loop.py`

```python
async def main():
    loop = HybridTradingLoop()
    
    # Инициализируем Telegram Commander
    commander = get_telegram_commander(
        executor=loop.futures_executor,
        ai_brain=loop.ai_brain,
        strategic_brain=loop.ai_brain.strategic_brain
    )
    
    # Запускаем в фоне
    commander_task = asyncio.create_task(commander.start())
    
    # Запускаем основной цикл
    await loop.run()
    
    # Останавливаем commander при выходе
    await commander.stop()
```

### Конфигурация

Использует существующие переменные из `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Как получить:**

1. **Bot Token:**
   - Открыть [@BotFather](https://t.me/BotFather)
   - `/newbot`
   - Следовать инструкциям
   - Скопировать токен

2. **Chat ID:**
   - Написать боту любое сообщение
   - Открыть: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Найти `"chat":{"id":123456789}`
   - Скопировать ID

### Безопасность

**Проверка админа:**
```python
def _is_admin(self, update: Update) -> bool:
    return str(update.effective_chat.id) == str(self.admin_chat_id)
```

**Игнорирование чужих:**
```python
async def ignore_non_admin(self, update: Update, context):
    if not self._is_admin(update):
        print(f"🚫 Ignored message from non-admin: {update.effective_chat.id}")
```

Только админ может:
- Видеть команды
- Получать ответы
- Активировать `/panic`

---

## 📊 СРАВНЕНИЕ: Старый vs Новый

### Старый `telegram_reporter.py`
❌ Спам уведомлениями о каждой сделке  
❌ Уведомления о funding rate  
❌ Уведомления о TP/SL  
❌ Нет интерактивности  
❌ Нельзя управлять ботом  

### Новый `telegram_commander.py`
✅ SILENT MODE - молчит по умолчанию  
✅ Интерактивные команды  
✅ Управление ботом (`/panic`)  
✅ Сводка по запросу (`/status`)  
✅ Экстренные уведомления только при ЧП  

---

## 🚀 DEPLOYMENT

### Шаг 1: Обновить requirements.txt ✅
```bash
# Уже есть в requirements.txt
python-telegram-bot==20.7
```

### Шаг 2: Обновить sklearn ✅
```bash
# requirements.txt
scikit-learn==1.6.1  # Было 1.3.2
```

### Шаг 3: Копирование файлов
```bash
scp Bybit_Trader/requirements.txt root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/telegram_commander.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/
```

### Шаг 4: Пересборка контейнера
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
```

### Шаг 5: Перезапуск
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Шаг 6: Проверка логов
```bash
ssh root@88.210.10.145 "docker logs -f bybit_bot | grep -E '(Telegram|Commander)'"
```

**Ожидаемый вывод:**
```
🤖 TelegramCommander initialized (SILENT MODE)
   Admin Chat ID: 123456789
✅ Telegram Commander started in background
✅ TelegramCommander started (polling)
```

---

## 🧪 ТЕСТИРОВАНИЕ

### 1. Проверка подключения
Открыть Telegram → Написать боту: `/start`

**Ожидаемый ответ:**
```
🤖 Bybit Trading Bot Commander

SILENT MODE - бот молчит по умолчанию
...
```

### 2. Проверка статуса
Написать: `/status`

**Ожидаемый ответ:**
```
📊 STATUS REPORT

💰 Balance: $379.10
...
```

### 3. Проверка безопасности
Попросить друга написать боту `/start`

**Ожидаемый результат:**
- Бот НЕ отвечает
- В логах: `🚫 Ignored message from non-admin: 987654321`

### 4. Проверка panic mode
Написать: `/panic`

**Ожидаемый результат:**
- Все позиции закрыты
- Бот перестал торговать
- Ответ: `✅ PANIC COMPLETE`

---

## 📝 ОТКЛЮЧЕНИЕ СТАРОГО REPORTER

### Вариант А: Удалить импорты (рекомендуется)

В файлах где используется `telegram_reporter.py`:
- `core/executors/futures_executor.py`
- `core/strategic_brain.py`
- и т.д.

Закомментировать:
```python
# from core.telegram_notifier import get_telegram_reporter
```

И все вызовы:
```python
# try:
#     reporter = get_telegram_reporter()
#     await reporter.notify_open(...)
# except Exception as e:
#     pass
```

### Вариант Б: Отключить в .env (быстрее)

```bash
# .env
TELEGRAM_BOT_TOKEN=  # Оставить пустым
TELEGRAM_CHAT_ID=    # Оставить пустым
```

Старый reporter не запустится, новый commander будет работать.

---

## 🎯 ПРЕИМУЩЕСТВА

### Для пользователя:
✅ **Тишина** - нет спама уведомлениями  
✅ **Контроль** - управление ботом из Telegram  
✅ **Безопасность** - только админ имеет доступ  
✅ **Экстренная остановка** - `/panic` в один клик  
✅ **Мониторинг** - статус по запросу  

### Для системы:
✅ **Меньше нагрузки** - нет постоянных отправок  
✅ **Асинхронность** - не блокирует торговлю  
✅ **Модульность** - легко добавить новые команды  
✅ **Graceful degradation** - если Telegram недоступен, бот продолжает работать  

---

## 🔮 БУДУЩИЕ УЛУЧШЕНИЯ

### Возможные команды:
- `/positions` - Список открытых позиций с деталями
- `/history` - Последние 10 сделок
- `/settings` - Изменить параметры (leverage, risk, etc.)
- `/pause` - Приостановить торговлю (без закрытия позиций)
- `/resume` - Возобновить торговлю
- `/stats` - Статистика за день/неделю/месяц

### Возможные уведомления:
- Большая прибыль (> $50 за сделку)
- Большой убыток (> $20 за сделку)
- Достижение целей (баланс $500, $1000, etc.)
- Новый режим Strategic Brain (BULL_RUSH, BEAR_CRASH)

---

## 📚 ДОКУМЕНТАЦИЯ

### Файлы:
- `core/telegram_commander.py` - Основной модуль
- `core/hybrid_loop.py` - Интеграция в основной цикл
- `TELEGRAM_COMMANDER_2025-12-12.md` - Этот файл

### Библиотека:
- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- Версия: 20.7
- Async/await support: ✅

---

**Автор:** Kiro AI  
**Дата:** 12 декабря 2025, 01:40 UTC  
**Статус:** ✅ Готово к деплою
