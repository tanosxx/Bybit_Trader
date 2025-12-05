# Deploy Strategic Brain - Quick Guide

**Дата:** 2025-12-05  
**Цель:** Внедрить Strategic Brain (Claude 3.5 Sonnet) как Gatekeeper Level 0

---

## 📦 Что изменилось

### Новые файлы
- ✅ `core/strategic_brain.py` - модуль Strategic Brain

### Изменённые файлы
- ✅ `core/ai_brain_local.py` - интеграция Strategic Brain
- ✅ `config.py` - добавлены настройки (ohmygpt_key, strategic_driver_url, strategic_model)
- ✅ `.env` - добавлен API ключ OHMYGPT_KEY
- ✅ `.env.example` - обновлён шаблон
- ✅ `requirements.txt` - добавлен openai==1.54.0

---

## 🚀 Команды деплоя

### 1. Копирование файлов

```bash
# Новый модуль
scp Bybit_Trader/core/strategic_brain.py root@88.210.10.145:/root/Bybit_Trader/core/

# Обновлённые файлы
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/.env root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/requirements.txt root@88.210.10.145:/root/Bybit_Trader/
```

### 2. Пересборка контейнера

```bash
# Остановка
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"

# Удаление старого контейнера (ОБЯЗАТЕЛЬНО!)
ssh root@88.210.10.145 "docker rm -f bybit_bot"

# Пересборка (установит openai==1.54.0)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# Запуск
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### 3. Проверка

```bash
# Логи запуска
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100"

# Проверка Strategic Brain
ssh root@88.210.10.145 "docker logs bybit_bot | grep 'Strategic Brain'"
```

---

## ✅ Ожидаемый результат

### Успешная инициализация

```
✅ Strategic Brain initialized (Model: claude-3-5-sonnet-20240620)
🧠 Local Brain analyzing BTCUSDT...
   🎯 Strategic Regime: SIDEWAYS
```

### Работа Gatekeeper

```
🚫 Strategic Veto: BUY blocked (Regime: BEAR_CRASH)
🚫 Strategic Veto: SELL blocked (Regime: BULL_RUSH)
```

---

## 🔍 Troubleshooting

### Проблема: "Strategic Brain client init failed"

**Причина:** API ключ не найден или неверный  
**Решение:** Проверить `.env` на сервере:
```bash
ssh root@88.210.10.145 "cat /root/Bybit_Trader/.env | grep OHMYGPT"
```

### Проблема: "Strategic Brain API Error"

**Причина:** OhMyGPT недоступен  
**Решение:** Это нормально! Бот автоматически fallback на SIDEWAYS (торгует как обычно)

### Проблема: Нет логов "Strategic Regime"

**Причина:** Модуль не загрузился  
**Решение:** Проверить импорты:
```bash
ssh root@88.210.10.145 "docker logs bybit_bot | grep -E '(ImportError|ModuleNotFoundError)'"
```

---

**Готово!** 🎉
