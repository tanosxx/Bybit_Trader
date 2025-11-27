# Bybit Crypto Trading Bot - Product Context

## 🎯 Цель проекта

Автоматический торговый бот для криптовалютной биржи Bybit с AI анализом, техническими индикаторами и Multi-Agent System.

## 🔍 Решаемые проблемы

1. **Эмоциональная торговля** - бот торгует без эмоций, строго по алгоритму
2. **24/7 мониторинг** - бот работает круглосуточно, не пропускает возможности
3. **Технический анализ** - автоматический расчет RSI, MACD, Bollinger Bands
4. **AI анализ** - умный анализ рынка через Gemini/Claude
5. **Управление рисками** - автоматический Stop Loss, Take Profit, лимиты

## 🆚 Отличия от PolyAI_Simulator

| Параметр | PolyAI_Simulator | Bybit_Trader |
|----------|------------------|--------------|
| Рынок | Polymarket (бинарные события) | Bybit (крипто) |
| Анализ | Текстовый (AI читает вопросы) | Технический (индикаторы) |
| Ликвидность | Низкая (многие рынки <$1000) | Высокая (BTC/ETH миллионы) |
| Предсказуемость | Низкая (политика, спорт) | Средняя (технические паттерны) |
| Время сделки | Часы/дни | Минуты/часы |
| Комиссии | 2% от прибыли | ~0.1% за сделку |

## 💡 Стратегия торговли

### Тип: Scalping / Day Trading
- Маленькие движения (0.5-2%)
- Быстрый вход/выход
- Много сделок в день

### Технические индикаторы:
1. **RSI (Relative Strength Index)**
   - RSI < 30 = Oversold → BUY signal
   - RSI > 70 = Overbought → SELL signal

2. **MACD (Moving Average Convergence Divergence)**
   - Bullish crossover → BUY signal
   - Bearish crossover → SELL signal

3. **Bollinger Bands**
   - Price < Lower Band → BUY signal
   - Price > Upper Band → SELL signal

### AI анализ:
- **Gemini 1.5 Flash** (FREE tier!) - первичный анализ
- **Claude 3.5 Haiku** (OpenRouter) - fallback
- **GPT-4o mini** (OpenRouter) - последний fallback

### Multi-Agent System:
- **Conservative Agent**: risk≤3, confidence≥0.80, position 10%
- **Balanced Agent**: risk≤6, confidence≥0.65, position 15%
- **Aggressive Agent**: risk≤8, confidence≥0.50, position 20%
- **Meta-Agent**: выбирает лучшего на основе последних 50 сделок

## 📊 Управление рисками

- **Stop Loss**: -2% от входа
- **Take Profit**: +3% от входа
- **Max открытых позиций**: 3
- **Max дневной убыток**: $5 (10% от баланса)
- **Max просадка**: -20% (emergency stop)
- **Размер позиции**: 10-20% от баланса

## 🎓 Обучение и адаптация

### Сбор данных:
- Исторические свечи (Bybit API)
- Результаты сделок (виртуальные + реальные)
- Технические индикаторы
- AI решения

### ML модель (будущее):
- LSTM для предсказания цены
- Reinforcement Learning для оптимизации
- Transfer Learning с готовых моделей

## 🚀 Roadmap

### Phase 1: Базовая инфраструктура (Week 1)
- ✅ Bybit API интеграция
- ✅ Технический анализ (RSI, MACD, BB)
- ✅ AI Brain (Gemini + OpenRouter)
- ✅ Database models
- ⏳ Trading loop
- ⏳ Dashboard

### Phase 2: Multi-Agent System (Week 2)
- ⏳ 3 агента (Conservative/Balanced/Aggressive)
- ⏳ Meta-agent
- ⏳ Dashboard интеграция

### Phase 3: Risk Management (Week 2)
- ⏳ Stop Loss / Take Profit
- ⏳ Position Sizer
- ⏳ Risk Manager
- ⏳ Emergency stop

### Phase 4: Telegram Integration (Week 3)
- ⏳ Уведомления о сделках
- ⏳ Ежедневная сводка
- ⏳ Алерты о рисках

### Phase 5: ML & Optimization (Week 4+)
- ⏳ LSTM price predictor
- ⏳ Reinforcement Learning
- ⏳ Backtesting
- ⏳ Parameter optimization

## 💰 Финансовые цели

**Стартовый капитал**: $50 (виртуальный)

**Целевые метрики:**
- Винрейт: >55%
- Средняя прибыль: +1.5% за сделку
- Средний убыток: -1.0% за сделку
- Risk/Reward: 1:1.5
- Месячная доходность: +10-20%

**Переход на реальные деньги:**
- После 100+ виртуальных сделок
- Винрейт >55%
- Просадка <15%
- Стабильная прибыль 2+ недели
