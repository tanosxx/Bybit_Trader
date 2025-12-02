-- Миграция: Добавление поля ml_features для Online Learning
-- Дата: 2025-12-02
-- Безопасно для работающей БД

-- Добавляем колонку ml_features (JSON)
ALTER TABLE trades 
ADD COLUMN IF NOT EXISTS ml_features JSON;

-- Проверка
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'trades' AND column_name = 'ml_features';
