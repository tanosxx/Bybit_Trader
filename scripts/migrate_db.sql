-- Migration: Add exit_reason and market_type columns
ALTER TABLE trades ADD COLUMN IF NOT EXISTS exit_reason VARCHAR(200);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS market_type VARCHAR(20) DEFAULT 'spot';
