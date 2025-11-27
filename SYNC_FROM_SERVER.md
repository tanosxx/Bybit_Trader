# 📥 Синхронизация файлов с сервера

## Проблема
Некоторые файлы были созданы только на сервере и отсутствуют в локальном репозитории.

## Решение

### 1. Подключиться к серверу
```bash
ssh root@88.210.10.145
```

### 2. Найти все файлы проекта Bybit_Trader
```bash
cd /root/Bybit_Trader
find . -type f -not -path "./.git/*" -not -path "./__pycache__/*" -not -path "./venv/*"
```

### 3. Скопировать файлы на локальную машину

#### Windows (PowerShell):
```powershell
# Скопировать весь проект
scp -r root@88.210.10.145:/root/Bybit_Trader/* C:\path\to\local\Bybit_Trader\

# Или отдельные файлы
scp root@88.210.10.145:/root/Bybit_Trader/core/*.py C:\path\to\local\Bybit_Trader\core\
scp root@88.210.10.145:/root/Bybit_Trader/web/*.py C:\path\to\local\Bybit_Trader\web\
scp root@88.210.10.145:/root/Bybit_Trader/scripts/*.py C:\path\to\local\Bybit_Trader\scripts\
```

#### Linux/Mac:
```bash
# Скопировать весь проект
scp -r root@88.210.10.145:/root/Bybit_Trader/* ~/Bybit_Trader/

# Или отдельные файлы
scp root@88.210.10.145:/root/Bybit_Trader/core/*.py ~/Bybit_Trader/core/
scp root@88.210.10.145:/root/Bybit_Trader/web/*.py ~/Bybit_Trader/web/
scp root@88.210.10.145:/root/Bybit_Trader/scripts/*.py ~/Bybit_Trader/scripts/
```

### 4. Проверить что скопировалось
```bash
# Локально
git status
git diff
```

### 5. Закоммитить изменения
```bash
git add .
git commit -m "Sync files from server"
git push
```

## Важные файлы для синхронизации

### Core модули:
- `core/bybit_api.py` - API клиент Bybit
- `core/ai_brain.py` - AI анализ (обновлен с 3 ключами)
- `core/real_trader.py` - Основной трейдер
- `core/risk_manager.py` - Управление рисками
- `core/technical_analysis.py` - Технический анализ
- `core/telegram_bot.py` - Telegram уведомления

### Database:
- `database/models.py` - Модели БД
- `database/init_db.py` - Инициализация БД

### Web:
- `web/dashboard.py` - Dashboard (ОБНОВЛЕН!)

### Scripts:
- `scripts/clean_old_trades.py` - Очистка старых сделок
- `scripts/test_*.py` - Тестовые скрипты

### Config:
- `.env` - Конфигурация (ОБНОВЛЕН с 3 Gemini ключами!)
- `config.py` - Настройки (ОБНОВЛЕН!)
- `requirements.txt` - Зависимости

## Автоматическая синхронизация (рекомендуется)

Создать скрипт `sync.bat` (Windows) или `sync.sh` (Linux):

```bash
#!/bin/bash
# sync.sh

SERVER="root@88.210.10.145"
REMOTE_PATH="/root/Bybit_Trader"
LOCAL_PATH="./Bybit_Trader"

echo "🔄 Синхронизация с сервера..."

# Копируем только исходники (без .env, БД, логов)
rsync -avz --exclude='.git' \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           --exclude='.env' \
           --exclude='*.db' \
           --exclude='logs/' \
           $SERVER:$REMOTE_PATH/ $LOCAL_PATH/

echo "✅ Синхронизация завершена!"
```

Сделать исполняемым:
```bash
chmod +x sync.sh
./sync.sh
```

## Проверка после синхронизации

1. Проверить что все файлы на месте:
```bash
ls -la Bybit_Trader/core/
ls -la Bybit_Trader/web/
ls -la Bybit_Trader/scripts/
```

2. Проверить .env (должны быть 3 Gemini ключа):
```bash
cat Bybit_Trader/.env | grep GOOGLE_API_KEY
```

3. Проверить config.py (должны быть 3 ключа):
```bash
cat Bybit_Trader/config.py | grep google_api_key
```

## Что НЕ копировать

❌ `.env` - содержит секреты (уже обновлен локально)  
❌ `__pycache__/` - кэш Python  
❌ `.git/` - история Git  
❌ `*.db` - база данных  
❌ `logs/` - логи  
❌ `venv/` - виртуальное окружение  

## Следующие шаги

После синхронизации:

1. ✅ Проверить что все файлы на месте
2. ✅ Обновить .env с 3 Gemini ключами
3. ✅ Закоммитить изменения в Git
4. ✅ Запушить на GitHub
5. ✅ Задеплоить на сервер (если нужно)

---

**Важно:** Всегда храни исходники локально и в Git! Сервер - только для запуска.
