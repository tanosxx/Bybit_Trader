"""
Создание таблицы ai_decisions для полного логирования AI решений
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from database.db import engine


async def create_table():
    """Создать таблицу ai_decisions"""
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS ai_decisions (
        id SERIAL PRIMARY KEY,
        time TIMESTAMP NOT NULL DEFAULT NOW(),
        symbol VARCHAR(20) NOT NULL,
        
        -- Рыночные данные
        price FLOAT,
        rsi FLOAT,
        macd VARCHAR(20),
        trend VARCHAR(50),
        
        -- News Brain
        news_sentiment VARCHAR(20),
        news_score FLOAT,
        
        -- ML Predictor
        ml_signal VARCHAR(10),
        ml_confidence FLOAT,
        ml_predicted_change FLOAT,
        
        -- Local Brain
        local_decision VARCHAR(10),
        local_confidence FLOAT,
        local_risk INTEGER,
        
        -- Multi-Agent
        agent_consensus BOOLEAN,
        agent_conservative BOOLEAN,
        agent_balanced BOOLEAN,
        agent_aggressive BOOLEAN,
        
        -- Futures Brain
        futures_action VARCHAR(10),
        futures_score INTEGER,
        futures_confidence FLOAT,
        futures_leverage INTEGER,
        
        -- Итог
        final_action VARCHAR(20),
        execution_reason VARCHAR(200),
        
        -- Extra
        extra_data JSONB
    );
    
    -- Индексы для быстрого поиска
    CREATE INDEX IF NOT EXISTS idx_ai_decisions_time ON ai_decisions(time);
    CREATE INDEX IF NOT EXISTS idx_ai_decisions_symbol ON ai_decisions(symbol);
    CREATE INDEX IF NOT EXISTS idx_ai_decisions_final_action ON ai_decisions(final_action);
    """
    
    async with engine.begin() as conn:
        await conn.execute(text(create_sql))
        print("✅ Таблица ai_decisions создана!")
        
        # Проверяем
        result = await conn.execute(text("SELECT COUNT(*) FROM ai_decisions"))
        count = result.scalar()
        print(f"📊 Записей в таблице: {count}")


if __name__ == "__main__":
    asyncio.run(create_table())
