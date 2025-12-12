"""
Патч для добавления проверки лимита позиций на символ
"""
import re

# Читаем файл
with open('core/executors/futures_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Паттерн для замены (после проверки 1)
old_pattern = r"""        # Проверка 2: Ордеров на этот символ
        symbol_orders = await self\._count_orders_for_symbol\(symbol\)
        if symbol_orders >= self\.max_orders_per_symbol:
            error_msg = f"❌ \{symbol\} limit: \{symbol_orders\}/\{self\.max_orders_per_symbol\} orders"
            print\(f"   \{error_msg\}"\)
            return ExecutionResult\(success=False, market_type=self\.market_type, error=error_msg\)"""

new_pattern = """        # Проверка 2: Позиций на этот символ (НОВОЕ v7.1!)
        symbol_positions = await self._count_positions_for_symbol(symbol)
        max_per_symbol = getattr(settings, 'futures_max_positions_per_symbol', 1)
        if symbol_positions >= max_per_symbol:
            error_msg = f"❌ {symbol} position limit: {symbol_positions}/{max_per_symbol} positions"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 3: Ордеров на этот символ
        symbol_orders = await self._count_orders_for_symbol(symbol)
        if symbol_orders >= self.max_orders_per_symbol:
            error_msg = f"❌ {symbol} limit: {symbol_orders}/{self.max_orders_per_symbol} orders"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)"""

# Заменяем все вхождения
content = re.sub(old_pattern, new_pattern, content)

# Обновляем версию в комментариях
content = content.replace('# 0. CHECK POSITION LIMITS (v6.2)', '# 0. CHECK POSITION LIMITS (v7.1)')
content = content.replace('# Проверка 3: Общее количество ордеров', '# Проверка 4: Общее количество ордеров')

# Сохраняем
with open('core/executors/futures_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Патч применён успешно!")
print("   - Добавлена проверка лимита позиций на символ")
print("   - Обновлена нумерация проверок")
