# Bybit_Trader - Конфигурация проекта

## Среда разработки и деплоя
- **Разработка**: Windows (локально) - ТОЛЬКО РЕДАКТИРОВАНИЕ КОДА
- **Продакшн**: Ubuntu VPS (IP: 88.210.10.145, Нидерланды)
- **Пользователь**: root
- **Процесс**: Редактируем локально → копируем на сервер
- **Контейнеризация**: Все работает только в Docker
- **Порты**: 5435 (PostgreSQL), 8585 (Dashboard)

### ⚠️ КРИТИЧЕСКОЕ ПРАВИЛО: НЕ ЗАПУСКАТЬ ЛОКАЛЬНО!
- ❌ **НИКОГДА** не запускать Docker локально
- ❌ **НИКОГДА** не запускать тесты локально
- ❌ **НИКОГДА** не запускать скрипты локально
- ✅ **ВСЕГДА** работать только на сервере (88.210.10.145)
- ✅ Локально только редактирование кода
- ✅ Все запуски, тесты, проверки - ТОЛЬКО на сервере через SSH

## Bybit API Credentials
```
API Key: lq2uoJ8GlfoEI1Kdgd
API Secret: hnW8T1Q3eT5DniNmBupmCuOVdm7FCv40byzM
Testnet: false (mainnet)
Permissions: Контракты, USDC контракты, Единый торговый аккаунт, СПОТ, Кошелек, Обмен, Earn
```

## Архитектура проекта
- **Язык**: Python 3.10+
- **БД**: PostgreSQL (Docker)
- **ORM**: SQLAlchemy (Async)
- **Dashboard**: Streamlit
- **AI**: Gemini 1.5 Flash (FREE tier!) + OpenRouter (Claude/GPT fallback)
- **Стартовый депозит**: $50 (виртуальный)

## Стратегия торговли
- **Тип**: Scalping / Day Trading
- **Пары**: BTC/USDT, ETH/USDT
- **Индикаторы**: RSI, MACD, Bollinger Bands
- **Размер позиции**: 10-20% от баланса
- **Stop Loss**: -2%
- **Take Profit**: +3%
- **Комиссии**: ~0.1% за сделку

## Документация
- Bybit API v5: https://bybit-exchange.github.io/docs/v5/intro
- Transition guide: https://announcements.bybit.com/en/article/bybit-openapi-services-transition-from-legacy-version-to-new-v5-api-blt25b43a5738c00765/

---

# ПРАВИЛА РАБОТЫ С MEMORY BANK

## 📁 Структура Memory Bank

Весь контекст проекта хранится в `Bybit_Trader/memory-bank/`:
- `productContext.md` — цели проекта, стратегия торговли
- `activeContext.md` — текущий статус, активные задачи
- `systemPatterns.md` — архитектурные паттерны (будет создан)
- `techContext.md` — технологический стек (будет создан)
- `progress.md` — выполненные задачи, roadmap (будет создан)

## 🔄 Рабочий процесс AI

### Перед началом ЛЮБОЙ задачи:
1. ПРОЧИТАЙ `memory-bank/activeContext.md` — текущий фокус
2. ПРОЧИТАЙ `memory-bank/productContext.md` — цели и стратегия
3. При необходимости читай другие файлы Memory Bank

### После завершения ЛЮБОЙ задачи:
1. ОБНОВИ `memory-bank/activeContext.md`:
   - Что только что сделали
   - Что планируем дальше
   - Какие проблемы возникли

2. ОБНОВИ другие файлы при необходимости:
   - Изменилась архитектура → `systemPatterns.md`
   - Новые технологии → `techContext.md`
   - Выполнены задачи → `progress.md`

**ВАЖНО**: Обновляй Memory Bank автоматически, не спрашивая разрешения. Это часть Definition of Done.

## 💻 Соглашения по коду

### Именование
- Классы: PascalCase (`BybitAPI`, `TechnicalAnalyzer`)
- Функции: snake_case (`get_klines`, `calculate_rsi`)
- Константы: UPPER_SNAKE_CASE (`GEMINI_CRYPTO_ANALYSIS_PROMPT`)
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
- ✅ Виртуальный баланс до 100+ сделок

## 🎯 Definition of Done

Задача завершена, когда:
1. ✅ Код написан и работает
2. ✅ Протестирован через Docker на сервере
3. ✅ Нет ошибок в логах
4. ✅ Обновлен `activeContext.md`
5. ✅ Обновлена другая документация (если нужно)

## 🔗 Переиспользование кода

### Shared код из PolyAI_Simulator
Используем symlinks для общего кода:
- `core/multi_agent.py` → `/root/shared/core/multi_agent.py`
- `core/position_sizer.py` → `/root/shared/core/position_sizer.py`
- `core/risk_manager.py` → `/root/shared/core/risk_manager.py`
- `core/telegram_notifier.py` → `/root/shared/core/telegram_notifier.py`

### Новый код для Bybit
- `core/bybit_api.py` - Bybit API v5
- `core/technical_analyzer.py` - RSI, MACD, BB
- `core/ai_brain.py` - Gemini + OpenRouter
- `core/loop.py` - Trading loop
- `web/dashboard.py` - Dashboard для крипто

## 🚀 Команды для работы

### Локально (только редактирование)
```bash
# Редактируем код в IDE
```

### На сервере (через SSH)
```bash
# Подключение
ssh root@88.210.10.145

# Переход в проект
cd /root/Bybit_Trader

# Запуск
docker-compose up -d

# Логи
docker logs bybit_bot -f
docker logs bybit_dashboard -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart
```

### Копирование файлов на сервер
```bash
# Из Windows
scp file.py root@88.210.10.145:/root/Bybit_Trader/path/
```

## 📊 Мониторинг

- **Dashboard**: http://88.210.10.145:8585
- **Логи бота**: `docker logs bybit_bot -f`
- **Логи dashboard**: `docker logs bybit_dashboard -f`
- **БД**: `docker exec -it bybit_db psql -U bybit_user -d bybit_trader`

## ⚠️ Важные замечания

1. **Виртуальный баланс** - не используем реальные деньги до 100+ сделок
2. **Gemini FREE tier** - может иметь rate limits, есть fallback на OpenRouter
3. **Bybit API** - используем v5 (новая версия)
4. **Комиссии** - ~0.1% за сделку (учитываем в расчетах)
5. **Stop Loss обязателен** - защита от больших убытков
