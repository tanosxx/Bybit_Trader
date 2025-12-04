-- Reset Trading Data - Очистка торговой истории
-- Сохраняем: candles (для ML), app_config (настройки)
-- Удаляем: trades, wallet_history, ai_decisions, system_logs

-- 1. Очистка сделок
TRUNCATE TABLE trades CASCADE;

-- 2. Очистка истории баланса
TRUNCATE TABLE wallet_history CASCADE;

-- 3. Очистка AI решений (опционально - можно оставить для анализа)
TRUNCATE TABLE ai_decisions CASCADE;

-- 4. Очистка системных логов
TRUNCATE TABLE system_logs CASCADE;

-- 5. Сброс виртуального баланса в app_config
UPDATE app_config 
SET value = '50.0' 
WHERE key = 'futures_virtual_balance';

-- Проверка результата
SELECT 'Trades cleared' as status, COUNT(*) as count FROM trades
UNION ALL
SELECT 'Wallet history cleared', COUNT(*) FROM wallet_history
UNION ALL
SELECT 'AI decisions cleared', COUNT(*) FROM ai_decisions
UNION ALL
SELECT 'System logs cleared', COUNT(*) FROM system_logs
UNION ALL
SELECT 'Candles preserved', COUNT(*) FROM candles;
