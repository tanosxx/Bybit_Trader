---
inclusion: always
---

# Bybit Trading Bot - Конфигурация проекта

## Среда разработки и деплоя
- **Разработка**: Windows (локально) - ТОЛЬКО РЕДАКТИРОВАНИЕ КОДА
- **Продакшн**: Ubuntu VPS (IP: 88.210.10.145, Нидерланды)
- **Пользователь**: root
- **Проект**: Bybit_Trader (автоматический торговый бот)
- **Контейнеризация**: Все работает только в Docker
- **Занятые сервисы**: vless VPN сервер + другая служба (проверять порты!)

### ⚠️ КРИТИЧЕСКОЕ ПРАВИЛО: НЕ ЗАПУСКАТЬ ЛОКАЛЬНО!
- ❌ **НИКОГДА** не запускать Docker локально
- ❌ **НИКОГДА** не запускать тесты локально
- ❌ **НИКОГДА** не запускать скрипты локально
- ❌ **НИКОГДА** не создавать bash скрипты для деплоя
- ✅ **ВСЕГДА** работать только на сервере (88.210.10.145)
- ✅ Локально только редактирование кода
- ✅ Все запуски, тесты, проверки - ТОЛЬКО на сервере через SSH
- ✅ AI сам выполняет SSH команды (пользователь только вводит пароль)

### 🔑 SSH ДОСТУП К СЕРВЕРУ
- **Пароль вводится ВРУЧНУЮ пользователем**
- **AI выполняет команды напрямую через SSH**
- **НЕ создавать bash скрипты** - выполнять команды по одной
- **Формат работы:**
  1. AI копирует файлы: `scp file.py root@88.210.10.145:/path/`
  2. AI выполняет команды: `ssh root@88.210.10.145 "команда"`
  3. Пользователь вводит пароль когда система просит
  4. AI проверяет результат и продолжает

### 🚨 ВАЖНО: Проверка баланса
**ВСЕГДА используй правильный стартовый баланс:**
```sql
-- Стартовый баланс = $100 (изменён 4 декабря 2025)
SELECT 100.0 + SUM(pnl) - SUM(fee_entry + fee_exit) as current_balance
FROM trades WHERE status = 'CLOSED' AND market_type = 'futures';
```

### 🐳 Docker Deployment Rules (ОБНОВЛЕНО 5 декабря 2025)

**НОВЫЙ СПОСОБ (с улучшенным Dockerfile):**
```bash
# 1. Копируем файлы
scp Bybit_Trader/core/file.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем (БЕЗ --no-cache, БЕЗ docker rm!)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# 3. Перезапускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

**Почему теперь НЕ нужно удалять контейнер:**
- ✅ Dockerfile использует раздельные слои (COPY core/, COPY web/, etc.)
- ✅ .dockerignore исключает ненужные файлы
- ✅ PYTHONDONTWRITEBYTECODE=1 отключает .pyc кэш
- ✅ Пересобирается только изменённый слой

**СТАРЫЙ СПОСОБ (если что-то сломалось):**
```bash
# Полная пересборка с нуля
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

**При изменении config.py или requirements.txt:**
```bash
# Нужна полная пересборка (эти файлы в ранних слоях)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
```

### 🔥 КРИТИЧЕСКАЯ ПРОБЛЕМА: Pydantic ValidationError "Extra inputs are not permitted"

**Симптомы:**
```
ValidationError: 3 validation errors for Settings
ohmygpt_key
  Extra inputs are not permitted [type=extra_forbidden]
strategic_driver_url
  Extra inputs are not permitted [type=extra_forbidden]
```

**Причина:**
Pydantic 2.10+ с `pydantic-settings` читает `.env` файл и валидирует ВСЕ переменные.
Если переменная есть в `.env`, но НЕ объявлена в классе `Settings`, Pydantic выдаёт ошибку,
даже если в `model_config` стоит `extra="ignore"`.

**РЕШЕНИЕ (проверенное):**

1. **НЕ добавлять переменные в класс Settings** (если они читаются через `os.getenv()`)
2. **Удалить переменные из `.env` файла на сервере**
3. **НЕ добавлять переменные в `docker-compose.yml` environment**
4. **Пересобрать образ БЕЗ кэша**

**Пошаговая инструкция:**

```bash
# 1. Удалить переменные из .env на сервере
ssh root@88.210.10.145 "cd /root/Bybit_Trader && sed -i '/^OHMYGPT_KEY=/d; /^STRATEGIC_DRIVER_URL=/d; /^STRATEGIC_MODEL=/d' .env"

# 2. Убедиться что переменных НЕТ в docker-compose.yml
# (они НЕ должны быть в секции environment: для сервиса bot)

# 3. Пересобрать образ БЕЗ кэша
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot && docker rm -f bybit_bot && docker-compose build --no-cache bot"

# 4. Запустить
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

**Почему это работает:**
- `.env` файл копируется в Docker образ при `COPY . .`
- Pydantic читает `.env` автоматически при инициализации Settings
- Если переменной нет в `.env`, Pydantic её не видит
- Модули читают переменные напрямую через `os.getenv()` из environment контейнера

**Альтернативное решение (НЕ рекомендуется):**
Добавить поля в Settings как Optional, но это создаёт путаницу:
```python
# ❌ НЕ ДЕЛАТЬ ТАК
ohmygpt_key: Optional[str] = None
strategic_driver_url: Optional[str] = None
```

**Правильный подход:**
```python
# ✅ В config.py - НЕ объявлять поля
# Комментарий для документации:
# Strategic Brain - Claude 3.5 Sonnet через OhMyGPT
# Примечание: эти настройки читаются напрямую через os.getenv() в strategic_brain.py
# чтобы избежать конфликтов с Pydantic validation

# ✅ В модуле - читать напрямую
import os
self.api_key = os.getenv("OHMYGPT_KEY")
```

**Проверка что проблема решена:**
```bash
# Логи должны показать успешный запуск
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50"

# Должны увидеть:
# ✅ Strategic Brain initialized (Model: claude-3-5-sonnet-20240620)
# 🧠 Local Brain analyzing BTCUSDT...
```

## 🏗️ Архитектура Bybit Trading Bot

### Технологический стек
- **Язык**: Python 3.10+
- **БД**: PostgreSQL 15 (Docker)
- **ORM**: SQLAlchemy (Async)
- **Dashboard**: Flask (порт 8585)
- **AI**: Gemini Flash 1.5 + OpenRouter (Claude 3.5 Haiku резерв)
- **ML**: TensorFlow 2.18 (LSTM), Scikit-learn, River (online learning)
- **Режим**: Demo Trading (Bybit Testnet)

### Docker Контейнеры (5 сервисов)
1. **bybit_bot** - Основной торговый бот (hybrid_loop.py)
2. **bybit_dashboard** - Web интерфейс (Flask, порт 8585)
3. **bybit_sync** - Синхронизация позиций с биржей
4. **bybit_monitor** - Мониторинг позиций
5. **bybit_db** - PostgreSQL база данных

### Конфигурация (config.py)
```python
# Баланс и риски
futures_virtual_balance: float = 50.0  # $50 стартовый капитал
futures_leverage: int = 5  # Плечо 5x (dynamic 2-7x)
futures_risk_per_trade: float = 0.20  # 20% от баланса
futures_margin_mode: 'ISOLATED'  # Изолированная маржа

# Simulated Realism (учёт комиссий)
estimated_fee_rate: float = 0.0006  # 0.06% Taker fee
min_profit_threshold_multiplier: float = 2.0  # Минимум 2× комиссия
simulate_fees_in_demo: bool = True

# Торговые пары
futures_pairs: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']

# Лимиты
futures_max_open_positions: int = 7
futures_max_orders_per_symbol: int = 15
futures_min_confidence: float = 0.50  # 50%

# Стопы
stop_loss_pct: float = 1.5  # -1.5%
take_profit_pct: float = 3.0  # +3.0%
trailing_stop_enabled: bool = True
```

### Торговая система (7 уровней фильтрации)

**Decision Tree:**
```
0. Strategic Brain (NEW! - раз в 4 часа)
   - Claude 3.5 Sonnet анализирует глобальный режим рынка
   - BULL_RUSH → только LONG
   - BEAR_CRASH → только SHORT
   - SIDEWAYS → всё разрешено
   - UNCERTAIN → НЕ торговать
   ↓
0.5. Strategic Veto (на каждый сигнал)
   - Блокирует неподходящие сигналы (BUY в BEAR_CRASH и т.д.)
   ↓
1. Trading Hours Check (24/7 - отключен)
   ↓
2. Gatekeeper Level 1: CHOP Filter
   - CHOP > 60 = флэт → SKIP
   - Защита от бокового рынка
   ↓
3. Gatekeeper Level 2: Pattern Filter
   - Historical Win Rate < 40% → SKIP
   - Анализ 1000 свечей, топ-10 паттернов
   ↓
4. ML Confidence Check
   - Raw Confidence < 55% → SKIP
   - LSTM v2 + Self-Learning (9,500+ samples)
   ↓
5. Fee Profitability Check
   - Gross Profit < 2× Total Fees → SKIP
   - Минимальный TP ~0.5-0.8%
   ↓
6. Futures Brain Multi-Agent
   - Score < 3/6 → SKIP
   - Conservative (вес 3): conf > 75%
   - Balanced (вес 2): conf > 60%
   - Aggressive (вес 1): conf > 55%
```

### ML Системы

**0. Strategic Brain (NEW! - Claude 3.5 Sonnet)**
- API: OhMyGPT (бонусный баланс, только Claude)
- Endpoint: `https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/`
- Модель: `claude-3-5-sonnet-20240620`
- Обновление: раз в 4 часа
- Режимы: BULL_RUSH, BEAR_CRASH, SIDEWAYS, UNCERTAIN
- Graceful degradation: fallback на SIDEWAYS при ошибке

**1. LSTM Model v2**
- Файл: `ml_training/models/bybit_lstm_model_v2.h5`
- Предсказывает направление цены
- Выход: BUY/SELL/HOLD + confidence

**2. Self-Learning (River ARF)**
- Файл: `ml_data/self_learner.pkl`
- Online learning: 9,500+ samples
- Accuracy: 90.3%
- Обучается на каждой сделке

**3. Scenario Tester**
- История: 1,000 свечей на символ
- Pattern matching: Euclidean Distance
- Анализирует топ-10 похожих паттернов
- Возвращает Historical Win Rate

**4. News Brain**
- Источники: CryptoPanic API
- Sentiment: VADER analysis
- Выход: EXTREME_FEAR → PANIC_SELL

### База данных (PostgreSQL)

**Таблицы:**
- `trades` - История сделок
- `candles` - Исторические свечи (62,582 записей)
- `wallet_history` - История баланса
- `ai_decisions` - Решения AI
- `system_logs` - Системные логи
- `app_config` - Конфигурация

**Важно:** При сбросе НЕ удалять `candles` - это ML данные!

### Dashboard (Flask)

**URL:** http://88.210.10.145:8585

**API Endpoints:**
- `/api/data` - Основные данные (баланс, сделки)
- `/api/ml/status` - Статус ML (learning count)
- `/api/system/status` - Статус систем (6 индикаторов)

**Обновление Dashboard:**
- При изменении HTML/JS: hard refresh (Ctrl+Shift+R)
- При изменении Python: пересборка контейнера
- Всегда удалять контейнер перед пересборкой!

### Стратегия торговли

**Тип:** Futures (фьючерсы USDT-M)
**Режим:** Demo Trading (виртуальный баланс $50)
**Стиль:** Trend following + Mean reversion
**Плечо:** Dynamic 2-7x (зависит от confidence)
**Risk/Reward:** 1:2 (SL 1.5% / TP 3.0%)

**Комиссии (Simulated):**
- Entry: 0.06% × Entry Value
- Exit: 0.06% × Exit Value
- Total: ~$0.12 на сделку $100

**Ожидаемая производительность:**
- Сделок в день: 5-15
- Win Rate: 30-50%
- Avg Trade: +$0.50 - $1.00 net
- Цель: не потерять депозит $50

---

## 🔧 КРИТИЧЕСКИЕ УРОКИ И ИСПРАВЛЕНИЯ (Декабрь 2025)

### 1. Strategic Compliance (5 декабря 2025)

**ПРОБЛЕМА:** Strategic Brain блокирует новые сигналы, но старые позиции остаются открытыми и закрываются по Stop Loss.

**РЕШЕНИЕ:** Создан `core/strategic_compliance.py`

**Логика:**
- **UNCERTAIN** → Закрыть ВСЕ позиции (Cash is King)
- **BEAR_CRASH** → Закрыть все LONG (только SHORT)
- **BULL_RUSH** → Закрыть все SHORT (только LONG)
- **SIDEWAYS** → Всё разрешено

**Интеграция:** В начале каждого цикла `hybrid_loop.py`:
```python
# Strategic Compliance Check
enforcer = get_compliance_enforcer()
positions_to_close = enforcer.enforce_strategic_compliance(
    active_positions, 
    current_regime
)
# Закрываем несоответствующие позиции
```

**Интервал обновления:** Снижен с 1 часа до 30 минут (0.5h)

### 2. Docker Кэширование и Dashboard (5 декабря 2025)

**ПРОБЛЕМА:** 
- Приходится удалять контейнер при каждом изменении
- Dashboard показывает фантомные позиции с биржи
- Старые данные не обновляются

**РЕШЕНИЕ 1: Улучшенный Dockerfile**
```dockerfile
# Раздельные слои (вместо COPY . .)
COPY config.py .
COPY core/ ./core/
COPY database/ ./database/
COPY web/ ./web/
COPY ml_training/ ./ml_training/
COPY ml_data/ ./ml_data/

# Отключить bytecode cache
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

**РЕШЕНИЕ 2: .dockerignore**
```
__pycache__/
*.pyc
*.md
!README.md
*.sh
*.bat
test_*.py
```

**РЕШЕНИЕ 3: API из БД (не с биржи)**
```python
async def get_futures_positions():
    """Получить позиции ИЗ БД (не с биржи!)"""
    # Берём только Trade.status == OPEN из БД
    # Игнорируем фантомные позиции с Bybit API
```

**Результат:**
- ✅ Образ: 43 MB → 24 MB
- ✅ Пересборка только изменённых слоёв
- ✅ Нет фантомных позиций
- ✅ Актуальные данные из БД

### 3. Neural HUD v2 (5 декабря 2025)

**Добавлено:**
- 🧠 **AI Reasoning Panel** - текстовое объяснение Strategic Brain
- 📰 **News Analysis** - анализ новостей и sentiment
- 🔄 **Decision Flow Diagram** - интерактивная схема 7 шагов фильтрации

**Архитектура:**
```
Bot → GlobalBrainState → brain_state.json (shared volume) → Dashboard API → Neural HUD
```

**Новые методы:**
```python
state.update_ai_reasoning(reasoning_text, news_analysis)
state.update_decision_flow(step, status, result, time_ms)
state.set_final_decision(action, reason)
```

**URL:** http://88.210.10.145:8585/brain

### 4. Баланс и Расчёты

**ВАЖНО:** Стартовый баланс = $100 (изменён с $50 4 декабря 2025)

**Правильный расчёт:**
```sql
SELECT 
    100.0 + SUM(pnl) - SUM(fee_entry + fee_exit) as current_balance
FROM trades 
WHERE status = 'CLOSED' AND market_type = 'futures';
```

**Текущий статус (5 декабря 2025):**
- Стартовый: $100.00
- Текущий: $111.31
- Profit: +$11.31 (+11.31%)
- Gross PnL: +$12.78
- Fees: -$1.47

---

## 📝 Документация проекта

### Основные файлы документации (Bybit_Trader/)
- `STRATEGIC_COMPLIANCE_FIX.md` - Strategic Compliance (5 дек 2025)
- `DASHBOARD_CACHE_FIX.md` - Docker кэширование (5 дек 2025)
- `NEURAL_HUD_V2_COMPLETE.md` - Neural HUD v2 (5 дек 2025)
- `SMART_GROWTH_100_CONFIG.md` - Конфигурация $100 (4 дек 2025)
- `SYSTEM_CHECK_FINAL.md` - Полная проверка систем
- `SIMULATED_REALISM.md` - Учёт комиссий

### Почему НЕ используется Memory Bank

**Memory Bank был для PolyAI_Simulator** (старый проект).  
**Сейчас работаем с Bybit_Trader** - это другой проект!

**Вместо Memory Bank используем:**
1. **Steering файл** (этот файл) - вся конфигурация
2. **Markdown документы** в Bybit_Trader/ - отчёты и логи
3. **Код как документация** - config.py, комментарии
4. **Git commits** - история изменений

**Преимущества:**
- ✅ Вся информация в одном месте (steering)
- ✅ Не нужно обновлять 5 разных файлов
- ✅ Меньше overhead, больше скорость
- ✅ Документы создаются по факту (DEPLOYMENT_LOG и т.д.)

**Если нужна история:**
- Читай последние .md файлы в Bybit_Trader/
- Смотри логи: `docker logs bybit_bot`
- Проверяй БД: `SELECT * FROM trades`

## 💻 Соглашения по коду

### Именование
- Классы: PascalCase (`TradingBot`, `AIBrain`)
- Функции: snake_case (`scan_markets`, `get_balance`)
- Константы: UPPER_SNAKE_CASE (`AI_ANALYSIS_PROMPT`)
- Async функции: всегда `async def`

### Структура файлов
```python
"""Docstring модуля на русском"""
# 1. Импорты стандартной библиотеки
# 2. Импорты сторонних библиотек
# 3. Локальные импорты
# 4. Код
# 5. Singleton (если нужен)
```

### Обработка ошибок
```python
try:
    result = await risky_operation()
except SpecificException as e:
    print(f"❌ Error: {e}")
    # Логирование в БД
    return default_value
```

## 🔐 Безопасность

- ❌ НИКОГДА не коммить `.env`
- ❌ НИКОГДА не хардкодить API ключи
- ✅ Всегда использовать `settings` из `config.py`
- ✅ Проверять `.gitignore` перед коммитом

## 🎯 Definition of Done

Задача завершена, когда:
1. ✅ Код написан и работает
2. ✅ Файлы скопированы на сервер (scp)
3. ✅ Контейнеры пересобраны и запущены
4. ✅ Протестирован через Docker (логи чистые)
5. ✅ Нет ошибок в логах
6. ✅ Создан отчёт .md (если крупное изменение)
7. ✅ Steering обновлён (если изменилась архитектура)

---

## 🔧 Частые проблемы и решения

### Проблема: Dashboard показывает фантомные позиции
**Причина:** API берёт данные с биржи вместо БД  
**Решение:** ИСПРАВЛЕНО 5 декабря 2025
- `get_futures_positions()` теперь берёт данные из БД
- Игнорирует фантомные позиции с Bybit API
- Показывает только реальные позиции из `trades` таблицы

### Проблема: Strategic Brain блокирует сигналы, но позиции остаются открытыми
**Причина:** Нет автоматического закрытия при смене режима  
**Решение:** ИСПРАВЛЕНО 5 декабря 2025
- Создан `strategic_compliance.py`
- Автоматически закрывает несоответствующие позиции
- UNCERTAIN → закрывает ВСЕ
- BEAR_CRASH → закрывает LONG
- BULL_RUSH → закрывает SHORT

### Проблема: Docker кэширует старый код
**Причина:** `COPY . .` кэширует весь проект как один слой  
**Решение:** ИСПРАВЛЕНО 5 декабря 2025
- Dockerfile использует раздельные слои
- `.dockerignore` исключает ненужное
- `PYTHONDONTWRITEBYTECODE=1` отключает .pyc
- Теперь НЕ нужно `docker rm -f` при каждом изменении

### Проблема: Dashboard показывает старые данные
**Причина:** Браузер кэширует API ответы  
**Решение:**
1. Hard refresh: Ctrl+Shift+R (или Ctrl+F5)
2. Проверить что API возвращает свежие данные: `curl http://88.210.10.145:8585/api/data`

### Проблема: Нет сделок (все SKIP)
**Причина:** Strategic Brain в режиме UNCERTAIN или Gatekeeper блокирует  
**Решение:** 
1. Проверить режим: `docker logs bybit_bot | grep "Strategic Regime"`
2. Если UNCERTAIN - это нормально, ждать изменения режима (30 минут)
3. Если CHOP > 60 - ждать трендового движения

### Проблема: Баланс не обновился после изменения config.py
**Причина:** config.py в раннем слое Docker  
**Решение:**
```bash
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Проблема: ML модель не загружается
**Причина:** Файл не найден или версия sklearn не совпадает  
**Решение:** Проверить логи:
```bash
docker logs bybit_bot | grep -E "(ML Model|Self-Learning|LSTM)"
```

### Проблема: Pydantic ValidationError "Extra inputs are not permitted"
**Причина:** Переменная в .env, но не объявлена в Settings  
**Решение:**
1. Удалить переменную из .env на сервере
2. ИЛИ добавить в Settings как Optional
3. Пересобрать контейнер БЕЗ кэша

### Проблема: RSS Feed Parsing Warnings
**Причина:** Некоторые RSS фиды имеют некорректный XML (syntax error, not well-formed)  
**Решение:** ИСПРАВЛЕНО 5 декабря 2025
- Улучшена обработка ошибок в `_fetch_feed()` метод
- Игнорируются некритичные XML ошибки (syntax error, not well-formed)
- Логируются только критичные ошибки (когда нет данных)
- Фиды продолжают работать даже с некорректным XML

---

## 📊 Мониторинг системы

### Проверка здоровья
```bash
# Все контейнеры
docker ps | grep bybit

# Логи бота (последние 100 строк)
docker logs bybit_bot --tail 100

# Статистика сделок
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT COUNT(*) as total, 
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
       ROUND(SUM(pnl)::numeric, 2) as total_pnl
FROM trades WHERE status = 'CLOSED';
"

# Проверка баланса
docker logs bybit_bot | grep "Virtual Balance"
```

### Ключевые метрики
- **CHOP < 60** - рынок в тренде, сделки возможны
- **Score >= 3/6** - агенты согласны, вход разрешён
- **Fee check passed** - сделка прибыльна после комиссий
- **Win Rate > 40%** - система работает хорошо

---

## 🚀 Быстрый старт после перезагрузки сервера

```bash
# 1. Подключиться к серверу
ssh root@88.210.10.145

# 2. Перейти в проект
cd /root/Bybit_Trader

# 3. Запустить все контейнеры
docker-compose up -d

# 4. Проверить логи
docker logs -f bybit_bot

# 5. Открыть Dashboard
# http://88.210.10.145:8585
```


---

## 🧠 Neural HUD - Real-Time AI Visualization

**URL:** http://88.210.10.145:8585/brain

### Что это?
Neural HUD - визуализация процесса принятия решений торгового бота в реальном времени.
Показывает "мысли" всех AI модулей без запросов к БД (только in-memory данные).

### Архитектура
```
Trading Bot → GlobalBrainState (In-Memory) → Flask API → Neural HUD (Auto-refresh 2s)
```

### Компоненты

**1. GlobalBrainState** (`core/state.py`)
- Singleton для хранения текущего состояния всех AI модулей
- Thread-safe (threading.Lock)
- Обновляется в реальном времени при работе бота
- НИКАКИХ запросов к БД

**2. Flask API** (`web/app.py`)
- Эндпоинт: `/api/brain_live`
- Возвращает: JSON с данными из GlobalBrainState
- Response time: <10ms
- No-cache headers для real-time обновлений

**3. Frontend** (`web/templates/brain.html`)
- Cyberpunk theme (тёмная тема с неоновыми эффектами)
- Auto-refresh каждые 2 секунды
- Responsive design

### Что показывает

**Strategic Brain (Генерал)**
- Режим рынка: BULL_RUSH / BEAR_CRASH / SIDEWAYS / UNCERTAIN
- Объяснение от Claude 3.5 Sonnet
- Обновление: раз в 4 часа

**Market Indicators**
- News Sentiment: -1.0 to +1.0 (VADER)
- Latest Headline: Последняя новость
- Bot Status: ACTIVE / OFFLINE
- Last Scan: Время последнего сканирования
- Total Decisions: Количество решений
- Active Positions: Открытые позиции

**Symbol Cards** (BTC, ETH, SOL, BNB, XRP)
- Current Price
- RSI (индикатор перекупленности)
- CHOP (индикатор флэта)
- ML Decision: BUY/SELL/HOLD + confidence
- Predicted Change: Ожидаемое изменение %
- Gatekeeper Status: PASS или BLOCK: Reason

### Интеграция в модули

**Импорт:**
```python
try:
    from core.state import get_global_brain_state
    STATE_AVAILABLE = True
except ImportError:
    STATE_AVAILABLE = False
```

**Обновление данных:**
```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        
        # Strategic Brain
        state.update_strategic(regime="BULL_RUSH", reason="Strong uptrend")
        
        # News
        state.update_news(sentiment=0.75, headline="Bitcoin breaks $50k", count=12)
        
        # Market Data
        state.update_market_data(symbol="BTCUSDT", chop=45.2, rsi=58.3, price=42150.50)
        
        # ML Predictions
        state.update_ml_prediction(symbol="BTCUSDT", decision="BUY", confidence=0.68, change_pct=1.2)
        
        # Gatekeeper
        state.update_gatekeeper(symbol="BTCUSDT", status="PASS")
        # или
        state.update_gatekeeper(symbol="ETHUSDT", status="BLOCK: CHOP 65.3")
        
        # Positions
        state.update_positions(positions=["BTCUSDT", "ETHUSDT"])
        
        # System Status
        state.update_system_status(running=True, scan_time=datetime.now())
    except Exception as e:
        pass  # Не критично
```

### Deployment

**Файлы:**
- `core/state.py` - GlobalBrainState
- `web/app.py` - Flask эндпоинты
- `web/templates/brain.html` - Frontend
- Обновлены: `core/strategic_brain.py`, `core/ai_brain_local.py`

**Деплой:**
```bash
# Копируем файлы
scp Bybit_Trader/core/state.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/strategic_brain.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/
scp Bybit_Trader/web/templates/brain.html root@88.210.10.145:/root/Bybit_Trader/web/templates/

# Пересобираем контейнеры
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot dashboard"
ssh root@88.210.10.145 "docker rm -f bybit_bot bybit_dashboard"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot dashboard"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot dashboard"
```

**Проверка:**
```bash
# API
curl http://88.210.10.145:8585/api/brain_live | jq .

# UI
# Открыть в браузере: http://88.210.10.145:8585/brain
```

### Performance
- Memory overhead: ~1-2 MB
- API response: <10ms
- Frontend refresh: 2 секунды
- Database load: 0 (только in-memory)

### Документация
- `NEURAL_HUD_README.md` - Главный README
- `NEURAL_HUD_QUICKSTART.md` - Быстрый старт
- `NEURAL_HUD_DEPLOYMENT.md` - Deployment guide
- `NEURAL_HUD_INTEGRATION_GUIDE.md` - Developer guide
- `NEURAL_HUD_COMPLETE.md` - Полный отчёт

---

## 📊 ТЕКУЩИЙ СТАТУС (12 декабря 2025, 01:20 UTC)

### Баланс и Производительность
- **Стартовый баланс:** $100.00
- **Текущий баланс:** $379.10
- **Profit:** +$279.10 (+279%)
- **Всего сделок:** 332 (125 реальных, 175 phantom closes, 32 открытых)
- **Win Rate:** 77.6% (97 wins / 28 losses из реальных сделок)

### Системы
- ✅ **Strategic Brain:** Gemini 2.5 Flash + Algion (GPTFree) fallback
- ✅ **Strategic Compliance:** Автоматическое закрытие позиций при смене режима
- ✅ **Neural HUD v2:** http://88.210.10.145:8585/brain
- ✅ **Dashboard:** http://88.210.10.145:8585 (данные из БД, нет фантомных позиций)
- ✅ **Docker:** Оптимизированный Dockerfile с раздельными слоями
- ✅ **BTC Correlation Filter:** "Папа решает всё" (блокирует неподходящие сигналы)
- ✅ **Self-Learning:** River ARF (9,690 samples, 90.49% accuracy)
- ✅ **Limit Orders (NEW!):** Maker Strategy v7.0 (0.02% fee vs 0.055%)

### Текущий режим
- **Strategic Regime:** SIDEWAYS
- **Открытых позиций:** 1
- **Order Type:** LIMIT (Maker fee 0.02%)

### Последние изменения (12 декабря 2025)
1. ✅ **Limit Order Strategy v7.0** - переход на Maker ордера
   - Экономия 63% на комиссиях входа (0.055% → 0.02%)
   - Умное ценообразование по Best Bid/Ask
   - Таймаут 60s с fallback на Market
   - Очистка зомби-ордеров перед каждым сигналом
   - Динамический расчёт комиссий (Maker vs Taker)
2. ✅ Algion (GPTFree) интеграция - fallback для Gemini
3. ✅ BTC Correlation Filter - блокирует сигналы против BTC тренда
4. ✅ Phantom Positions Fix - Sync Service корректно закрывает фантомные позиции
5. ✅ Full System Check - единый скрипт диагностики
6. ✅ Trade Verification - подтверждено 125 реальных сделок

---

## 💎 LIMIT ORDER STRATEGY (v7.0) - 12 декабря 2025

### Концепция
Переход с Market ордеров (Taker) на Limit ордера (Maker) для снижения комиссий.

**Экономия:** 63% на комиссиях входа = **$0.035 на каждую сделку $100**

### Комиссии Bybit
- **Maker (Limit):** 0.02% - когда ордер добавляет ликвидность в стакан
- **Taker (Market):** 0.055% - когда ордер забирает ликвидность из стакана

### Логика работы

**Шаг 1: Очистка зомби-ордеров**
```python
await cancel_all_active_orders(symbol)
```
Перед каждым новым сигналом удаляем старые ордера.

**Шаг 2: Получение Best Bid/Ask**
```python
best_prices = await get_best_prices(symbol)
# {'bid': 94999.5, 'ask': 95000.5}
```

**Шаг 3: Умное ценообразование**
- **BUY (LONG):** Limit Order по Best Bid (становимся в очередь покупателей)
- **SELL (SHORT):** Limit Order по Best Ask (становимся в очередь продавцов)

**Шаг 4: Размещение Limit Order**
```python
params = {
    "orderType": "Limit",
    "price": best_bid,  # или best_ask
    "timeInForce": "GTC"  # Good Till Cancel
}
```

**Шаг 5: Мониторинг исполнения (60s)**
- Проверяем статус каждые 2 секунды
- Если исполнен → Entry fee 0.02% ✅
- Если таймаут → Fallback на Market (0.055%)

**Шаг 6: Fallback на Market**
Если Limit не исполнился за 60s:
1. Отменяем Limit Order
2. Размещаем Market Order
3. Entry fee 0.055% (но сигнал не потерян!)

### Конфигурация

```python
# config.py
order_type: Literal['LIMIT', 'MARKET'] = 'LIMIT'
order_timeout_seconds: int = 60
limit_order_fallback_to_market: bool = True
maker_fee_rate: float = 0.0002  # 0.02%
taker_fee_rate: float = 0.00055  # 0.055%
```

### Ожидаемые результаты

**Maker Fill Rate:** 70% (цель)
- 70% сделок исполняются как Maker (0.02%)
- 30% сделок fallback на Taker (0.055%)

**Средняя комиссия входа:** ~0.03%
- Было: 0.055%
- Стало: (0.02 × 0.7) + (0.055 × 0.3) = 0.0305%
- **Экономия: 44% на средней комиссии!**

**Месячная экономия:**
- Сделок в день: 5-15
- Экономия на сделку: $0.035
- Экономия в день: $0.15 - $0.45
- **Экономия в месяц: $4.50 - $13.50**

При балансе $379 это **1.2% - 3.6% дополнительной прибыли в месяц!**

### Мониторинг

**SQL: Maker Fill Rate**
```sql
SELECT 
    COUNT(*) FILTER (WHERE extra_data->>'order_type' = 'LIMIT') as limit_orders,
    COUNT(*) as total_orders,
    ROUND(COUNT(*) FILTER (WHERE extra_data->>'order_type' = 'LIMIT')::numeric / COUNT(*) * 100, 1) as maker_fill_rate
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours';
```

**SQL: Средняя комиссия**
```sql
SELECT 
    extra_data->>'order_type' as order_type,
    COUNT(*) as count,
    ROUND(AVG(fee_entry)::numeric, 4) as avg_entry_fee,
    ROUND(AVG(fee_entry / (entry_price * quantity) * 100)::numeric, 3) as avg_fee_pct
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours'
GROUP BY extra_data->>'order_type';
```

**SQL: Экономия**
```sql
SELECT 
    SUM(CASE 
        WHEN extra_data->>'order_type' = 'LIMIT' 
        THEN (entry_price * quantity * 0.00055) - fee_entry 
        ELSE 0 
    END) as total_savings
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours';
```

### Документация
- `LIMIT_ORDER_STRATEGY_2025-12-12.md` - полная документация
- `DEPLOYMENT_LIMIT_ORDERS_2025-12-12.md` - отчёт о деплое

---

**Дата последнего обновления:** 2025-12-12 01:20 UTC
