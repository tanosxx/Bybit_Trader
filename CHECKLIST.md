# ✅ Чеклист - Что нужно сделать

## 🎯 Критические задачи (СДЕЛАТЬ СЕЙЧАС!)

### 1. ⚡ Задеплоить обновления на сервер

**Вариант A: Автоматический (рекомендуется)**
```bash
cd Bybit_Trader
./DEPLOY_UPDATES.sh  # Linux/Mac
# или
DEPLOY_UPDATES.bat   # Windows
```

**Вариант B: Ручной**
```bash
# Скопировать файлы
scp config.py root@88.210.10.145:/root/Bybit_Trader/
scp core/ai_brain.py root@88.210.10.145:/root/Bybit_Trader/core/
scp web/dashboard.py root@88.210.10.145:/root/Bybit_Trader/web/

# Обновить .env
ssh root@88.210.10.145
cd /root/Bybit_Trader
nano .env
# Добавить GOOGLE_API_KEY_1/2/3 и BYBIT_BASE_URL
# Удалить старую строку GOOGLE_API_KEY=...

# Перезапустить
docker-compose down
docker-compose up -d --build
```

**Статус:** ⬜ Не сделано

---

### 2. 🔍 Проверить работу

#### A. Dashboard
- Открыть: http://88.210.10.145:8585
- Проверить:
  - ⬜ Индикатор "🎮 DEMO TRADING" отображается
  - ⬜ Современный дизайн с градиентами
  - ⬜ График баланса работает
  - ⬜ Открытые позиции отображаются
  - ⬜ История сделок работает
  - ⬜ Статистика AI отображается

#### B. Логи бота
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose logs -f bybit_trader
```

Проверить:
- ⬜ "✅ Gemini (ключ #1, ...)" в логах
- ⬜ "✅ Gemini (ключ #2, ...)" в логах
- ⬜ Ротация между ключами работает
- ⬜ Нет ошибок подключения к API

#### C. Проверка .env на сервере
```bash
ssh root@88.210.10.145
cat /root/Bybit_Trader/.env | grep GOOGLE_API_KEY
```

Должно быть:
- ⬜ GOOGLE_API_KEY_1=...
- ⬜ GOOGLE_API_KEY_2=...
- ⬜ GOOGLE_API_KEY_3=...
- ⬜ НЕТ старой строки GOOGLE_API_KEY=...

---

### 3. 📥 Синхронизировать файлы с сервера

Если на сервере есть файлы, которых нет локально:

```bash
# Вариант A: rsync (рекомендуется)
rsync -avz --exclude='.git' \
           --exclude='__pycache__' \
           --exclude='.env' \
           --exclude='*.db' \
           root@88.210.10.145:/root/Bybit_Trader/ ./Bybit_Trader/

# Вариант B: scp
scp -r root@88.210.10.145:/root/Bybit_Trader/* ./Bybit_Trader/
```

Проверить:
- ⬜ Все файлы из `core/` скопированы
- ⬜ Все файлы из `web/` скопированы
- ⬜ Все файлы из `scripts/` скопированы
- ⬜ Все файлы из `database/` скопированы

**Статус:** ⬜ Не сделано

---

### 4. 💾 Закоммитить изменения в Git

```bash
cd Bybit_Trader
git status
git add .
git commit -m "Fix: Gemini keys to .env, new Dashboard, deploy scripts"
git push
```

Проверить:
- ⬜ Все новые файлы добавлены
- ⬜ Изменения закоммичены
- ⬜ Запушено на GitHub

**Статус:** ⬜ Не сделано

---

## 📊 Дополнительные задачи (можно позже)

### 5. 📈 Мониторинг работы

- ⬜ Проверять Dashboard каждый час
- ⬜ Следить за логами бота
- ⬜ Проверять ротацию Gemini ключей
- ⬜ Мониторить открытые позиции

### 6. 📚 Документация

- ⬜ Прочитать `QUICK_START.md`
- ⬜ Прочитать `UPDATES_LOG.md`
- ⬜ Прочитать `SYNC_FROM_SERVER.md`

### 7. 🔧 Оптимизация

- ⬜ Собрать статистику (100+ сделок)
- ⬜ Проанализировать винрейт
- ⬜ Оптимизировать параметры
- ⬜ Настроить стратегию

### 8. 💰 Переход на реальные деньги

- ⬜ Убедиться что винрейт > 60%
- ⬜ Убедиться что PnL положительный
- ⬜ Изменить `BYBIT_BASE_URL` на `https://api.bybit.com`
- ⬜ Получить реальные API ключи
- ⬜ Начать с малых сумм

---

## 🚨 Проблемы и решения

### Dashboard не открывается
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose ps
docker-compose logs dashboard
docker-compose restart dashboard
```

### Бот не торгует
```bash
docker-compose logs bybit_trader
# Проверь ошибки в логах
# Проверь баланс на Bybit
# Проверь что Demo режим активен
```

### Gemini ключи не работают
```bash
# Проверь .env
cat /root/Bybit_Trader/.env | grep GOOGLE_API_KEY

# Проверь логи
docker-compose logs bybit_trader | grep Gemini

# Перезапусти
docker-compose restart bybit_trader
```

### База данных пустая
```bash
# Пересоздай БД
docker-compose down -v
docker-compose up -d
```

---

## 📋 Итоговый чеклист

### Критические (СЕЙЧАС):
- ⬜ 1. Задеплоить обновления
- ⬜ 2. Проверить Dashboard
- ⬜ 3. Проверить логи бота
- ⬜ 4. Синхронизировать файлы
- ⬜ 5. Закоммитить в Git

### Важные (СЕГОДНЯ):
- ⬜ 6. Мониторить работу бота
- ⬜ 7. Проверить ротацию ключей
- ⬜ 8. Проверить сделки

### Дополнительные (НА НЕДЕЛЕ):
- ⬜ 9. Собрать статистику
- ⬜ 10. Оптимизировать параметры

---

## 🎯 Цель

**Бот должен:**
- ✅ Работать на Demo балансе
- ✅ Использовать 3 Gemini ключа с ротацией
- ✅ Показывать статистику на Dashboard
- ✅ Торговать автоматически
- ⏳ Собрать 100+ сделок
- ⏳ Показать винрейт > 60%
- ⏳ Перейти на реальные деньги

---

**Начни с пункта 1! 🚀**
