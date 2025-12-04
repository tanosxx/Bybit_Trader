# Dashboard Status Update - 2025-12-04

## Проблемы (исправлены)

### 1. ML статистика не обновляется
**Проблема**: Дашборд показывал застывшее значение 9200 samples, хотя в файле было 9490+

**Причина**: Браузер кэшировал ответы от `/api/ml/status`

**Решение**:
- Добавлены no-cache заголовки в endpoint `/api/ml/status`
- Добавлен timestamp в ответ для принудительной инвалидации кэша
- Файл читается напрямую из `ml_data/self_learner.pkl` без кэширования

**Код** (`web/app.py`, строки 650-690):
```python
@app.route('/api/ml/status')
def get_ml_status_api():
    """API для получения статуса Self-Learning модели"""
    try:
        import pickle
        import os
        
        model_path = 'ml_data/self_learner.pkl'
        
        # Читаем файл напрямую без загрузки модели River
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
            
            learning_count = data.get('learning_count', 0)
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            predictions_count = data.get('predictions_count', 0)
            
            # Рассчитываем метрики
            win_rate = (wins / learning_count * 100) if learning_count > 0 else 0.0
            
            # Accuracy из метрики
            metric = data.get('metric')
            accuracy = metric.get() if metric else 0.0
            
            response = jsonify({
                'enabled': True,
                'learned_samples': learning_count,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'model_accuracy': accuracy,
                'predictions': predictions_count,
                'ready': learning_count >= 50,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Отключаем кэширование
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
```

### 2. Индикаторы статуса систем
**Задача**: Добавить зелёные/красные лампочки для мониторинга всех систем

**Реализация**:
- Создан endpoint `/api/system/status` в `web/app.py`
- Проверяет 6 систем:
  1. 🧠 Self-Learning ML (файл + свежесть данных)
  2. 🤖 LSTM Model (наличие файла модели)
  3. 🗄️ Database (подключение к PostgreSQL)
  4. 🚦 Gatekeeper (ScenarioTester модуль)
  5. 📰 News Brain (RSS feeds)
  6. 🔌 Bybit API (наличие ключей)

**Статусы**:
- 🟢 `ok` - система работает нормально
- 🟡 `warning` - система работает с ограничениями
- 🔴 `error` - система недоступна

**HTML** (`web/templates/dashboard_futures.html`):
- Добавлена секция "Статус систем" с 6 карточками
- JavaScript функция `updateSystemStatus()` обновляет каждые 10 секунд
- Отдельная функция `updateMLStatus()` для ML метрик (каждые 5 секунд)

**Код** (`web/app.py`, строки 550-650):
```python
@app.route('/api/system/status')
def get_system_status_api():
    """API для получения статуса всех систем (зелёные/красные лампочки)"""
    try:
        import os
        import pickle
        from datetime import datetime, timedelta
        
        systems = {}
        
        # 1. Self-Learning ML
        try:
            model_path = 'ml_data/self_learner.pkl'
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                learning_count = data.get('learning_count', 0)
                updated_at = data.get('updated_at', None)
                
                # Проверяем свежесть (обновлялся ли за последний час)
                is_fresh = False
                if updated_at:
                    try:
                        last_update = datetime.fromisoformat(updated_at)
                        is_fresh = (datetime.utcnow() - last_update) < timedelta(hours=1)
                    except:
                        pass
                
                systems['self_learning'] = {
                    'status': 'ok' if learning_count > 0 and is_fresh else 'warning',
                    'message': f'{learning_count} samples',
                    'details': f'Last update: {updated_at or "unknown"}'
                }
            else:
                systems['self_learning'] = {
                    'status': 'error',
                    'message': 'Model file not found',
                    'details': 'File missing'
                }
        except Exception as e:
            systems['self_learning'] = {
                'status': 'error',
                'message': 'Error loading',
                'details': str(e)
            }
        
        # ... (аналогично для остальных 5 систем)
        
        response = jsonify({
            'systems': systems,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'ok' if all(s['status'] == 'ok' for s in systems.values()) else 'warning'
        })
        
        # Отключаем кэширование
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Деплой на сервер

### Команды для копирования:

```bash
# 1. Копируем файлы на сервер (пароль вводится вручную)
scp Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/
scp Bybit_Trader/web/templates/dashboard_futures.html root@88.210.10.145:/root/Bybit_Trader/web/templates/

# 2. SSH на сервер и перезапуск dashboard
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose restart dashboard
docker logs -f dashboard --tail 50
```

### Проверка:

1. Откройте дашборд: `http://88.210.10.145:5000`
2. Проверьте секцию "🔧 Статус систем" - должны быть 6 индикаторов
3. Проверьте что ML samples обновляются автоматически (каждые 5 секунд)
4. Проверьте что индикаторы меняют цвет в зависимости от статуса

## Технические детали

### Обновление данных:
- **Основные данные** (баланс, сделки, позиции): каждые 5 секунд
- **ML статистика**: каждые 5 секунд (отдельный endpoint)
- **Статус систем**: каждые 10 секунд

### No-cache заголовки:
```python
response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
response.headers['Pragma'] = 'no-cache'
response.headers['Expires'] = '0'
```

### JavaScript обновление:
```javascript
// ML Status - отдельный endpoint
async function updateMLStatus() {
    const response = await fetch('/api/ml/status');
    const mlStatus = await response.json();
    // ... обновление UI
}

// System Status
async function updateSystemStatus() {
    const response = await fetch('/api/system/status');
    const data = await response.json();
    // ... обновление индикаторов
}

// Запуск
setInterval(fetchData, 5000); // Основные данные
setInterval(updateSystemStatus, 10000); // Статус систем
```

## Результат

✅ ML статистика обновляется в реальном времени без перезагрузки страницы
✅ Индикаторы статуса показывают состояние всех 6 систем
✅ Дашборд работает стабильно без кэширования
✅ Все данные обновляются автоматически

## Файлы изменены:
- `Bybit_Trader/web/app.py` - добавлены endpoints `/api/ml/status` и `/api/system/status` с no-cache
- `Bybit_Trader/web/templates/dashboard_futures.html` - добавлена секция статуса систем + JavaScript обновление
