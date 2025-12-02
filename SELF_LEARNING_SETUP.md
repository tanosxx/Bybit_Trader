# 🧠 Self-Learning Module - Setup Guide

## Что это?

Online Learning система, которая учится на результатах реальных сделок:
- При входе: собирает фичи рынка (RSI, volatility, trend, etc.)
- При выходе: учится на результате (Win/Loss)
- Постоянно улучшает предсказания

**Безопасность:** Если модуль падает, бот продолжает работать по старой логике!

---

## 📋 Шаг 1: Обновление БД

### Вариант А: Автоматическая миграция (PostgreSQL)

```bash
# На сервере
ssh root@88.210.10.145
cd /root/Bybit_Trader

# Применяем миграцию
docker exec -i bybit_db psql -U bybit_user -d bybit_trader < database/migrations/add_ml_features.sql

# Проверяем
docker exec -i bybit_db psql -U bybit_user -d bybit_trader -c "SELECT column_name FROM information_schema.columns WHERE table_name='trades' AND column_name='ml_features';"
```

### Вариант Б: Ручная миграция

```sql
-- Подключаемся к БД
docker exec -it bybit_db psql -U bybit_user -d bybit_trader

-- Добавляем колонку
ALTER TABLE trades ADD COLUMN IF NOT EXISTS ml_features JSON;

-- Проверяем
\d trades
```

---

## 📦 Шаг 2: Установка зависимостей

```bash
# На сервере
cd /root/Bybit_Trader

# Обновляем requirements.txt (уже сделано)
# Пересобираем контейнеры
docker-compose down
docker-compose up -d --build
```

---

## 🚀 Шаг 3: Проверка работы

### Проверка логов бота

```bash
docker logs -f bybit_bot | grep -E "Self-Learning|🧠"
```

Должны видеть:
```
🧠 SelfLearner initialized:
   Model: ml_data/self_learner.pkl
   Status: ✅ Active
```

### Проверка предсказаний

После 50+ сделок должны видеть:
```
🧠 Self-Learning: 0.65 (conf: 0.23)
```

### Проверка обучения

При закрытии позиций:
```
🧠 Self-Learning: Learned from WIN
   Total samples: 127, Win rate: 54.3%
```

---

## 📊 Как это работает?

### 1. При входе в сделку (AI Brain)

```python
# Собираем фичи
ml_features = {
    'rsi': 45.2,
    'macd_bullish': 1.0,
    'trend_up': 0.0,
    'volatility': 0.023,
    'news_score': 0.15,
    'ml_confidence': 0.75
}

# Получаем предсказание
win_probability = self_learner.predict(ml_features)

# Взвешиваем: 80% Static ML + 20% Self-Learning
final_confidence = (static_ml * 0.8) + (self_learning * 0.2)
```

### 2. При выходе из сделки (Position Monitor)

```python
# Определяем результат
result = 1 if pnl > 0 else 0  # 1 = Win, 0 = Loss

# Обучаем модель
self_learner.learn(ml_features, result)
```

---

## 🔧 Настройки

### Веса в AI Brain

```python
# В ai_brain_local.py, строка ~480
# Взвешивание: 80% Static ML + 20% Self-Learning
final_confidence = (final_confidence * 0.8) + (self_learning_score * 0.2)
```

Можно изменить веса:
- `0.8` / `0.2` - консервативно (по умолчанию)
- `0.7` / `0.3` - больше доверия Self-Learning
- `0.9` / `0.1` - минимальное влияние

### Минимум сэмплов для активации

```python
# В self_learning.py, строка ~150
if self.learning_count < 50:  # Минимум 50 сделок
    return 0.5, 0.0  # Нейтральный результат
```

---

## 📈 Мониторинг

### Статистика Self-Learning

```python
# В Python консоли
from core.self_learning import get_self_learner

learner = get_self_learner()
stats = learner.get_stats()

print(stats)
# {
#     'enabled': True,
#     'predictions': 342,
#     'learned_samples': 127,
#     'wins': 69,
#     'losses': 58,
#     'win_rate': 54.3,
#     'model_accuracy': 0.58,
#     'ready': True
# }
```

### Файл модели

```bash
# Модель сохраняется в
ls -lh ml_data/self_learner.pkl

# Размер ~100-500KB
```

---

## 🐛 Troubleshooting

### Ошибка: "River not installed"

```bash
# Установить вручную
docker exec -it bybit_bot pip install river==0.21.0
```

### Ошибка: "column ml_features does not exist"

```bash
# Применить миграцию
docker exec -i bybit_db psql -U bybit_user -d bybit_trader < database/migrations/add_ml_features.sql
```

### Self-Learning не активируется

Проверить:
1. River установлен: `docker exec bybit_bot pip show river`
2. Колонка ml_features существует в БД
3. Минимум 50 сделок для активации

---

## 🎯 Ожидаемые результаты

### Первые 50 сделок
- Self-Learning **НЕ влияет** на решения (собирает данные)
- Бот работает по старой логике

### После 50+ сделок
- Self-Learning **активируется** (20% веса)
- Постепенное улучшение точности предсказаний
- Win rate должен расти на 2-5%

### После 200+ сделок
- Модель полностью обучена
- Адаптируется к текущим рыночным условиям
- Может давать +5-10% к Win Rate

---

## ⚠️ Важно!

1. **Graceful Degradation:** Если Self-Learning падает, бот продолжает работать
2. **Не удалять файл модели:** `ml_data/self_learner.pkl` содержит всё обучение
3. **Бэкапы:** Периодически копировать файл модели
4. **Сброс модели:** Удалить файл для начала обучения с нуля

---

## 📝 Changelog

- **2025-12-02:** Initial release
  - River ARF Classifier
  - 10 features (RSI, MACD, BB, Trend, Volatility, Volume, News, ML)
  - 80/20 weighting with Static ML
  - Graceful degradation
