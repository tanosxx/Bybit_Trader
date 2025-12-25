# Deployment: Adaptive Scalper Fix - 25 декабря 2025

**Время деплоя:** 19:15 UTC  
**Статус:** ✅ Успешно задеплоено  
**Версия:** config.py v2.1 (CHOP thresholds + TTL optimization)

---

## 📦 Что задеплоено

### Изменения в config.py

**1. CHOP Пороги (борьба с "вялым сползанием")**
```python
# БЫЛО:
chop_flat_threshold: float = 62.0  # CHOP >= 62 = FLAT
chop_trend_threshold: float = 55.0  # CHOP <= 55 = TREND

# СТАЛО:
chop_flat_threshold: float = 50.0  # CHOP >= 50 = FLAT (было 62)
chop_trend_threshold: float = 45.0  # CHOP <= 45 = TREND (было 55)
```

**Эффект:**
- CHOP 50-60 теперь активирует **FLAT режим** (Adaptive Scalper)
- Короткие TP/SL: TP 1.5% (вместо 3%), SL 1.05% (вместо 1.5%)
- Быстрый выход из позиций

**2. TTL (Time To Live) - глобальное снижение**
```python
# БЫЛО:
max_hold_time_minutes: int = 180  # 3 часа

# СТАЛО:
max_hold_time_minutes: int = 120  # 2 часа (было 180)
```

**Adaptive TTL:**
- FLAT режим: **60 минут** (120÷2)
- TREND режим: **120 минут**

**3. Комментарии про Phantom Closes**
Добавлены инструкции по диагностике Sync Service для борьбы с фантомными позициями.

---

## 🚀 Процесс деплоя

### Команды выполнены
```bash
# 1. Копирование config.py
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
✅ Успешно

# 2. Остановка контейнера
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
✅ Успешно

# 3. Удаление контейнера
ssh root@88.210.10.145 "docker rm -f bybit_bot"
✅ Успешно

# 4. Пересборка БЕЗ кэша (config.py в раннем слое)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
✅ Успешно (образ 183b9f0e5486)

# 5. Запуск контейнера
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
✅ Успешно
```

### Время деплоя
- Копирование: 2 сек
- Остановка: 5 сек
- Пересборка: ~3 минуты
- Запуск: 3 сек
- **Общее время: ~3.5 минуты**

---

## ✅ Проверка работы

### Логи бота (первый цикл)
```
🧠 Strategic Brain: Analyzing market regime...
✅ Strategic Brain: Market Regime = SIDEWAYS

📊 Analyzing BTCUSDT...
   🚀 Mode: TREND (ML Follower) - CHOP: 41.6
   
📊 Analyzing SOLUSDT...
   🚀 Mode: TREND (ML Follower) - CHOP: 38.1
```

**Результат:**
- ✅ CHOP 38.1 и 41.6 = **TREND режим** (правильно, т.к. < 45)
- ✅ Новые пороги применились
- ✅ Бот работает стабильно

### Текущие позиции
```sql
SOLUSDT BUY @ $124.00
Duration: 126 минут (старая позиция)
TTL: 180 минут (старый лимит)
```

**Примечание:** Старая позиция закроется по старому TTL (180 мин). Новые позиции будут использовать TTL 120 мин.

---

## 📊 Ожидаемые результаты

### Сценарии работы

**Сценарий 1: CHOP < 45 (Сильный тренд)**
- Режим: TREND
- TP: 3%, SL: 1.5%
- TTL: **120 минут** (было 180)
- Leverage: Dynamic 2-7x

**Сценарий 2: CHOP 45-50 (Гистерезис)**
- Режим: Сохраняется текущий
- Избегаем частых переключений

**Сценарий 3: CHOP >= 50 (Флэт / Вялое сползание)**
- Режим: **FLAT (Adaptive Scalper)**
- TP: **1.5%** (3% × 0.5)
- SL: **1.05%** (1.5% × 0.7)
- TTL: **60 минут** (120÷2)
- Быстрый выход!

### Целевые метрики (24 часа)
- ✅ Средняя длительность: **60-90 минут** (было 180)
- ✅ Zombie trades: **< 30%** (было 78%)
- ✅ Win Rate: **> 40%** (было 11%)
- ✅ Прибыльность: **> 0** (было -$4.65/день)

---

## 🔍 Мониторинг

### Команды для проверки

**1. Логи (режим и CHOP)**
```bash
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50 | grep -E '(CHOP|Mode:|TTL)'"
```

**2. Текущие позиции**
```bash
ssh root@88.210.10.145 "docker exec bybit_db psql -U bybit_user -d bybit_trader -c \"SELECT symbol, side, entry_price, pnl, EXTRACT(EPOCH FROM (NOW() - entry_time))/60 as duration_min FROM trades WHERE status = 'OPEN';\""
```

**3. Статистика за 24 часа**
```bash
ssh root@88.210.10.145 "docker exec bybit_db psql -U bybit_user -d bybit_trader -c \"SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE pnl > 0) as wins, ROUND(AVG(EXTRACT(EPOCH FROM (exit_time - entry_time))/60)::numeric, 1) as avg_duration_min FROM trades WHERE status = 'CLOSED' AND entry_time > NOW() - INTERVAL '24 hours';\""
```

### Dashboards
- Main: http://88.210.10.145:8585
- Neural HUD: http://88.210.10.145:8585/brain

---

## 🎯 Следующие шаги

### Мониторинг (24 часа)
1. Проверить среднюю длительность сделок
2. Проверить % zombie trades
3. Проверить Win Rate
4. Проверить прибыльность

### Если результаты хорошие
- Оставить настройки как есть
- Обновить steering файл

### Если результаты плохие
- Откатить изменения (вернуть старые пороги)
- Попробовать другие значения

### Возможные корректировки
- Если слишком много сделок → увеличить CHOP thresholds
- Если слишком мало сделок → уменьшить CHOP thresholds
- Если много убытков → увеличить TTL
- Если много зависаний → уменьшить TTL

---

## 📝 Откат (если нужно)

### Вернуть старые значения
```python
# В config.py:
chop_flat_threshold: float = 62.0  # было 50.0
chop_trend_threshold: float = 55.0  # было 45.0
max_hold_time_minutes: int = 180  # было 120
```

### Задеплоить
```bash
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot && docker rm -f bybit_bot && docker-compose build --no-cache bot && docker-compose up -d bot"
```

---

## 📚 Документация

### Созданные файлы
- `ADAPTIVE_SCALPER_FIX_2025-12-25.md` - Анализ проблемы и решение
- `DEPLOYMENT_ADAPTIVE_SCALPER_2025-12-25.md` - Этот файл (отчёт о деплое)

### Обновлённые файлы
- `config.py` - Новые CHOP пороги и TTL

---

**Статус:** ✅ Деплой завершён успешно  
**Риск:** Низкий  
**Rollback:** Простой (5 минут)  
**Мониторинг:** 24 часа
