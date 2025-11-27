# 🚀 Quick Start - Bybit Trading Bot

## Что было исправлено сегодня (2024-11-26)

### ✅ 1. Gemini ключи вынесены в .env
- Было: 3 ключа захардкожены в коде
- Стало: Все в `.env` файле (безопасно!)

### ✅ 2. Demo Bybit настроен
- Добавлен `BYBIT_BASE_URL=https://api-demo.bybit.com`
- Теперь явно указан Demo режим

### ✅ 3. Dashboard полностью переделан
- Современный дизайн
- Реальные данные из БД
- Графики, статистика, фильтры
- Информация по AI моделям

### ✅ 4. Инструкции созданы
- `SYNC_FROM_SERVER.md` - как копировать файлы
- `DEPLOY_UPDATES.bat/sh` - автоматический деплой
- `UPDATES_LOG.md` - детальный лог изменений

---

## 📋 Что нужно сделать СЕЙЧАС

### Вариант 1: Автоматический деплой (рекомендуется)

**Windows:**
```cmd
cd Bybit_Trader
DEPLOY_UPDATES.bat
```

**Linux/Mac:**
```bash
cd Bybit_Trader
chmod +x DEPLOY_UPDATES.sh
./DEPLOY_UPDATES.sh
```

### Вариант 2: Ручной деплой

1. **Скопировать файлы на сервер:**
```bash
scp config.py root@88.210.10.145:/root/Bybit_Trader/
scp core/ai_brain.py root@88.210.10.145:/root/Bybit_Trader/core/
scp web/dashboard.py root@88.210.10.145:/root/Bybit_Trader/web/
```

2. **Обновить .env на сервере:**
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
nano .env
```

Добавить:
```env
# AI APIs - Gemini (3 ключа для ротации)
GOOGLE_API_KEY_1=AIzaSyCalj1ugvpU1thqDtROGCEgIGdXDFBIOJM
GOOGLE_API_KEY_2=AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c
GOOGLE_API_KEY_3=AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c

# Bybit Demo URL
BYBIT_BASE_URL=https://api-demo.bybit.com
```

Удалить старую строку:
```env
GOOGLE_API_KEY=...  # Удалить эту строку!
```

3. **Перезапустить Docker:**
```bash
cd /root/Bybit_Trader
docker-compose down
docker-compose up -d --build
```

4. **Проверить логи:**
```bash
docker-compose logs -f
```

---

## 🔍 Проверка работы

### 1. Dashboard
Открыть: http://88.210.10.145:8585

Должно быть:
- ✅ Индикатор "🎮 DEMO TRADING"
- ✅ Текущий баланс
- ✅ График баланса
- ✅ Открытые позиции
- ✅ История сделок
- ✅ Статистика AI

### 2. Логи бота
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose logs -f bybit_trader
```

Должно быть:
- ✅ "✅ Gemini (ключ #1, gemini-2.0-flash-lite): ..."
- ✅ "✅ Gemini (ключ #2, gemini-2.0-flash-lite): ..."
- ✅ Ротация между ключами при лимитах

### 3. Проверка ротации ключей
Смотри в логах:
```
✅ Gemini (ключ #1, gemini-2.0-flash-lite): BUY (риск: 4, уверенность: 75%)
⚠️ Ключ #1, gemini-2.0-flash-lite: лимит исчерпан
✅ Gemini (ключ #2, gemini-2.5-flash-lite): SELL (риск: 3, уверенность: 80%)
```

---

## 📊 Структура проекта

```
Bybit_Trader/
├── core/
│   ├── bybit_api.py          # API клиент Bybit
│   ├── ai_brain.py           # AI анализ (ОБНОВЛЕН!)
│   ├── real_trader.py        # Основной трейдер
│   ├── risk_manager.py       # Управление рисками
│   ├── technical_analysis.py # Технический анализ
│   └── telegram_bot.py       # Telegram уведомления
├── database/
│   ├── models.py             # Модели БД
│   └── init_db.py            # Инициализация БД
├── web/
│   └── dashboard.py          # Dashboard (ОБНОВЛЕН!)
├── scripts/
│   └── clean_old_trades.py   # Очистка старых сделок
├── config.py                 # Конфигурация (ОБНОВЛЕН!)
├── .env                      # Переменные окружения (ОБНОВЛЕН!)
├── docker-compose.yml        # Docker конфигурация
├── Dockerfile                # Docker образ
└── requirements.txt          # Зависимости Python
```

---

## 🎯 Следующие шаги

1. ✅ Задеплоить обновления (см. выше)
2. ✅ Проверить Dashboard
3. ✅ Проверить ротацию Gemini ключей в логах
4. ✅ Мониторить сделки
5. ⏳ Собрать статистику (100+ сделок)
6. ⏳ Оптимизировать параметры
7. ⏳ Перейти на реальные деньги (когда будешь готов)

---

## 🆘 Проблемы?

### Dashboard не открывается
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose ps
docker-compose logs dashboard
```

### Бот не торгует
```bash
docker-compose logs bybit_trader
# Проверь логи на ошибки
```

### Gemini ключи не работают
```bash
# Проверь .env на сервере
ssh root@88.210.10.145
cat /root/Bybit_Trader/.env | grep GOOGLE_API_KEY
```

### База данных пустая
```bash
# Пересоздай БД
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose down -v
docker-compose up -d
```

---

## 📚 Документация

- `SYNC_FROM_SERVER.md` - Синхронизация файлов с сервера
- `UPDATES_LOG.md` - Детальный лог всех изменений
- `DEPLOY_UPDATES.bat/sh` - Автоматический деплой
- `SUCCESS.md` - История успешного запуска
- `README.md` - Основная документация

---

**Важно:** Теперь все исходники хранятся локально! Сервер только для запуска.
