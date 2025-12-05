# Strategic Brain Integration - Claude 3.5 Sonnet

**Дата:** 2025-12-05  
**Статус:** ✅ Готово к деплою

---

## 🎯 Что это?

**Strategic Brain** - высокоуровневый анализатор рыночного режима на базе **Claude 3.5 Sonnet**.

Работает как **Gatekeeper Level 0** (самый первый фильтр перед всеми остальными):
- Определяет глобальный режим рынка раз в **4 часа**
- Блокирует неподходящие сигналы (например, LONG в медвежьем рынке)
- Использует **бонусный баланс OhMyGPT** (работает только с Claude)

---

## 🏗️ Архитектура

### Модули

1. **`core/strategic_brain.py`** - Основной модуль
   - Класс `StrategicBrain` - анализатор режима
   - Функция `get_strategic_brain()` - singleton
   - 4 режима рынка: `BULL_RUSH`, `BEAR_CRASH`, `SIDEWAYS`, `UNCERTAIN`

2. **Интеграция в `ai_brain_local.py`**
   - Gatekeeper Level 0: проверка режима перед всеми фильтрами
   - Gatekeeper Level 0.5: вето на сигналы (блокирует BUY в BEAR_CRASH и т.д.)

### Decision Tree (обновлённый)

```
0. Strategic Brain (раз в 4 часа)
   → BULL_RUSH: только LONG
   → BEAR_CRASH: только SHORT
   → SIDEWAYS: всё разрешено
   → UNCERTAIN: НЕ торговать
   ↓
0.5. Strategic Veto (на каждый сигнал)
   → Блокирует неподходящие сигналы
   ↓
1. CHOP Filter (CHOP > 60 = флэт)
   ↓
2. Pattern Filter (Historical WR < 25%)
   ↓
3. ML Confidence (LSTM v2 + Self-Learning)
   ↓
4. Fee Profitability (TP > 0.6%)
   ↓
5. Futures Brain (Multi-Agent Score >= 3/6)
```

---

## 🔧 Конфигурация

### 1. Переменные окружения (`.env`)

```bash
# Strategic Brain - Claude 3.5 Sonnet через OhMyGPT
OHMYGPT_KEY=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
STRATEGIC_DRIVER_URL=https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/
STRATEGIC_MODEL=claude-3-5-sonnet-20240620
```

**ВАЖНО:**
- `STRATEGIC_DRIVER_URL` - **ОБЯЗАТЕЛЬНО** этот адрес (бонусный баланс работает только с ним!)
- `STRATEGIC_MODEL` - **ОБЯЗАТЕЛЬНО** Claude (модели GPT не съедят бонус)

### 2. Config.py

Добавлены настройки:
```python
ohmygpt_key: Optional[str] = None
strategic_driver_url: str = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/"
strategic_model: str = "claude-3-5-sonnet-20240620"
```

### 3. Requirements.txt

Добавлена зависимость:
```
openai==1.54.0  # OpenAI-compatible API для OhMyGPT
```

---

## 📊 Режимы рынка

### 1. BULL_RUSH (Агрессивный рост)
- **Разрешено:** только LONG (BUY)
- **Заблокировано:** SHORT (SELL)
- **Когда:** Сильный восходящий тренд, бычий моментум

### 2. BEAR_CRASH (Агрессивное падение)
- **Разрешено:** только SHORT (SELL)
- **Заблокировано:** LONG (BUY)
- **Когда:** Сильный нисходящий тренд, медвежье давление

### 3. SIDEWAYS (Боковик)
- **Разрешено:** LONG и SHORT
- **Заблокировано:** ничего
- **Когда:** Рынок без чёткого направления (default режим)

### 4. UNCERTAIN (Неопределённость)
- **Разрешено:** ничего
- **Заблокировано:** ВСЁ (не торгуем)
- **Когда:** Высокая волатильность, конфликтующие сигналы, риск новостей

---

## 🔄 Логика работы

### Обновление режима (раз в 4 часа)

1. **Сбор данных:**
   - Дневные свечи BTC и ETH (7 дней)
   - Сводка новостей от News Brain (24 часа)

2. **Запрос к Claude:**
   ```
   Промпт: "Analyze market structure. Choose regime: BULL_RUSH/BEAR_CRASH/SIDEWAYS/UNCERTAIN"
   Ответ: "BULL_RUSH" (только название режима)
   ```

3. **Кэширование:**
   - Режим сохраняется на 4 часа
   - Следующий запрос только через 4 часа

### Проверка сигнала (на каждый сигнал)

```python
# Gatekeeper Level 0.5: Strategic Veto
if strategic_regime == REGIME_BEAR_CRASH and signal == "BUY":
    return SKIP  # Блокируем LONG в медвежьем рынке

if strategic_regime == REGIME_BULL_RUSH and signal == "SELL":
    return SKIP  # Блокируем SHORT в бычьем рынке

if strategic_regime == REGIME_UNCERTAIN:
    return SKIP  # Не торгуем в неопределённости
```

---

## 🛡️ Graceful Degradation

**Если Strategic Brain недоступен:**
- ❌ API ключ не найден
- ❌ Сервис OhMyGPT недоступен
- ❌ Ошибка парсинга ответа

**Fallback:**
- Режим автоматически устанавливается в `SIDEWAYS`
- Бот продолжает работать как обычно (все сигналы разрешены)
- **НЕ роняет бота!**

```python
try:
    regime = await strategic_brain.get_market_regime(...)
except Exception as e:
    print(f"⚠️ Strategic Brain error: {e}")
    regime = REGIME_SIDEWAYS  # Fallback - торгуем как обычно
```

---

## 📈 Ожидаемый эффект

### Преимущества

1. **Фильтрация трендов:**
   - Не лонгим в медвежьем рынке
   - Не шортим в бычьем рынке
   - Снижение убыточных сделок на 15-25%

2. **Защита от волатильности:**
   - Режим `UNCERTAIN` блокирует торговлю в хаосе
   - Защита депозита в периоды высокого риска

3. **Бонусный баланс:**
   - Используем бесплатный баланс OhMyGPT
   - Нет затрат на API (пока баланс не кончится)

### Недостатки

1. **Пропуск сигналов:**
   - Может заблокировать хорошие контртрендовые сделки
   - Снижение количества сделок на 10-20%

2. **Зависимость от API:**
   - Если OhMyGPT недоступен, fallback на SIDEWAYS
   - Но это не критично (бот продолжает работать)

---

## 🚀 Деплой

### 1. Копирование файлов на сервер

```bash
# Копируем новый модуль
scp Bybit_Trader/core/strategic_brain.py root@88.210.10.145:/root/Bybit_Trader/core/

# Копируем обновлённый AI Brain
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/

# Копируем конфиги
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/.env root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/requirements.txt root@88.210.10.145:/root/Bybit_Trader/
```

### 2. Пересборка контейнера

```bash
# Останавливаем бота
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"

# Удаляем старый контейнер (ОБЯЗАТЕЛЬНО!)
ssh root@88.210.10.145 "docker rm -f bybit_bot"

# Пересобираем образ (установит openai==1.54.0)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# Запускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### 3. Проверка логов

```bash
# Смотрим логи запуска
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100"

# Ищем инициализацию Strategic Brain
ssh root@88.210.10.145 "docker logs bybit_bot | grep 'Strategic Brain'"

# Ожидаемый вывод:
# ✅ Strategic Brain initialized (Model: claude-3-5-sonnet-20240620)
# 🎯 Strategic Regime: SIDEWAYS
```

---

## 🧪 Тестирование

### 1. Проверка инициализации

```bash
docker logs bybit_bot | grep -E "(Strategic Brain|Strategic Regime)"
```

**Ожидаемый вывод:**
```
✅ Strategic Brain initialized (Model: claude-3-5-sonnet-20240620)
🎯 Strategic Regime: SIDEWAYS
```

### 2. Проверка работы Gatekeeper

```bash
docker logs bybit_bot | grep "Strategic Veto"
```

**Примеры:**
```
🚫 Strategic Veto: BUY blocked (Regime: BEAR_CRASH)
🚫 Strategic Veto: SELL blocked (Regime: BULL_RUSH)
🚫 Strategic Veto: ALL signals blocked (Regime: UNCERTAIN)
```

### 3. Проверка обновления режима

```bash
docker logs bybit_bot | grep "Strategic Brain: Analyzing"
```

**Ожидаемый вывод (раз в 4 часа):**
```
🧠 Strategic Brain: Analyzing market regime...
✅ Strategic Brain: Market Regime = SIDEWAYS
   → Claude Response: SIDEWAYS
```

---

## 📝 Примеры логов

### Успешная инициализация

```
✅ Strategic Brain initialized (Model: claude-3-5-sonnet-20240620)
🧠 Local Brain analyzing BTCUSDT...
   🎯 Strategic Regime: SIDEWAYS
   📰 News Sentiment: NEUTRAL (score: 0.00)
   🤖 ML Signal: BUY (conf: 65%, change: +1.20%)
   ✅ Final Decision: BUY (conf: 70%, risk: 5/10)
```

### Блокировка сигнала

```
🧠 Local Brain analyzing ETHUSDT...
   🎯 Strategic Regime: BEAR_CRASH
   📰 News Sentiment: FEAR (score: -0.45)
   🤖 ML Signal: BUY (conf: 68%, change: +0.80%)
   🚫 Strategic Veto: BUY blocked in BEAR_CRASH regime
   ✅ Final Decision: SKIP
```

### Fallback при ошибке

```
⚠️ Strategic Brain API Error: Connection timeout
   → Fallback to SIDEWAYS regime (safe mode)
🧠 Local Brain analyzing SOLUSDT...
   🎯 Strategic Regime: SIDEWAYS (fallback)
   📰 News Sentiment: NEUTRAL (score: 0.00)
   🤖 ML Signal: SELL (conf: 62%, change: -0.90%)
   ✅ Final Decision: SELL (conf: 65%, risk: 6/10)
```

---

## 🔍 Мониторинг

### Ключевые метрики

1. **Частота обновления режима:**
   - Должно быть раз в 4 часа
   - Проверка: `grep "Strategic Brain: Analyzing" logs`

2. **Количество блокировок:**
   - Сколько сигналов заблокировано Strategic Veto
   - Проверка: `grep "Strategic Veto" logs | wc -l`

3. **Распределение режимов:**
   - Сколько времени в каждом режиме
   - Проверка: `grep "Strategic Regime:" logs | sort | uniq -c`

4. **Ошибки API:**
   - Частота fallback на SIDEWAYS
   - Проверка: `grep "Strategic Brain API Error" logs`

---

## ⚠️ Важные замечания

1. **Бонусный баланс OhMyGPT:**
   - Работает только с Claude моделями
   - Работает только с URL `https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/`
   - Не менять эти параметры!

2. **Graceful Degradation:**
   - Если API недоступен, бот НЕ падает
   - Автоматический fallback на SIDEWAYS (торгуем как обычно)

3. **Кэширование:**
   - Режим обновляется раз в 4 часа
   - Между обновлениями используется кэшированное значение
   - Экономия API запросов

4. **Приоритет:**
   - Strategic Brain - самый первый фильтр (Level 0)
   - Если он блокирует, остальные фильтры не проверяются

---

## 📚 Дополнительно

### Файлы изменены

- ✅ `core/strategic_brain.py` - новый модуль
- ✅ `core/ai_brain_local.py` - интеграция Strategic Brain
- ✅ `config.py` - добавлены настройки
- ✅ `.env` - добавлен API ключ
- ✅ `.env.example` - обновлён шаблон
- ✅ `requirements.txt` - добавлен openai==1.54.0

### Steering обновлён

Добавлена секция в `polymarket-project.md`:
```markdown
### Strategic Brain
- Claude 3.5 Sonnet через OhMyGPT
- Gatekeeper Level 0 (высокоуровневый фильтр)
- 4 режима: BULL_RUSH, BEAR_CRASH, SIDEWAYS, UNCERTAIN
- Обновление раз в 4 часа
```

---

**Готово к деплою!** 🚀
