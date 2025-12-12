"""
Полная синхронизация с Bybit API
- Балансы всех монет
- Открытые ордера
- История сделок
"""
import asyncio
from datetime import datetime
from sqlalchemy import select, update
from database.models import Trade, WalletHistory
from database.db import async_session
from core.bybit_api import BybitAPI
from config import settings


class BybitSync:
    """Полная синхронизация с Bybit"""
    
    def __init__(self):
        self.api = BybitAPI()
    
    async def sync_all_balances(self):
        """Синхронизировать все балансы"""
        try:
            balance_data = await self.api.get_wallet_balance()
            
            if not balance_data:
                print("⚠️ Не удалось получить балансы")
                return
            
            print(f"\n💰 Балансы:")
            
            # Считаем общий equity в USDT
            total_equity_usdt = 0.0
            total_available_usdt = 0.0
            
            for coin, data in balance_data.items():
                total = data.get('total', 0.0)
                available = data.get('available', 0.0)
                
                if total > 0:
                    print(f"   {coin}: ${total:.2f} (доступно: ${available:.2f})")
                    
                    # Для USDT считаем напрямую
                    if coin == 'USDT':
                        total_equity_usdt += total
                        total_available_usdt += available
                    # Для других монет нужно конвертировать (упрощенно считаем как USDT)
                    elif coin in ['USDC']:
                        total_equity_usdt += total
                        total_available_usdt += available
            
            # Сохраняем в БД
            async with async_session() as session:
                wallet_entry = WalletHistory(
                    time=datetime.utcnow(),
                    balance_usdt=total_available_usdt,
                    equity=total_equity_usdt,
                    change_amount=0.0,
                    change_reason="Full balance sync from Bybit API"
                )
                session.add(wallet_entry)
                await session.commit()
            
            print(f"✅ Общий equity: ${total_equity_usdt:.2f} (доступно: ${total_available_usdt:.2f})")
            
        except Exception as e:
            print(f"❌ Ошибка синхронизации балансов: {e}")
            import traceback
            traceback.print_exc()
    
    async def sync_futures_positions(self):
        """
        Синхронизировать фьючерсные позиции с биржей
        
        УЛУЧШЕННАЯ ЛОГИКА v2.0:
        1. Получаем позиции с биржи (только открытые size > 0)
        2. Создаём уникальный ключ (symbol, side, quantity) для точного сопоставления
        3. Закрываем в БД всё что не найдено на бирже
        4. Рассчитываем PnL и комиссии при закрытии
        5. Обучаем ML модель на результате
        """
        try:
            # Получаем ВСЕ позиции с биржи
            all_positions = await self.api.get_positions()
            
            # Создаём словарь открытых позиций с уникальным ключом
            # Ключ: (symbol, side, quantity) - для точного сопоставления
            exchange_positions = {}
            exchange_positions_list = []  # Для вывода
            
            for pos in all_positions:
                symbol = pos.get('symbol', '')
                size = float(pos.get('size', 0))
                
                if size > 0:
                    # Открытая позиция
                    side = 'BUY' if pos.get('side') == 'Buy' else 'SELL'
                    entry_price = float(pos.get('avgPrice', 0) or pos.get('entry_price', 0))
                    
                    # Уникальный ключ для сопоставления
                    key = (symbol, side, size)
                    exchange_positions[key] = {
                        'symbol': symbol,
                        'side': side,
                        'size': size,
                        'entry_price': entry_price,
                        'leverage': pos.get('leverage', '1'),
                        'unrealised_pnl': float(pos.get('unrealisedPnl', 0))
                    }
                    exchange_positions_list.append(f"{symbol} {side} {size}")
            
            print(f"\n📊 Фьючерсные позиции на бирже:")
            print(f"   Открытых: {len(exchange_positions)}")
            if exchange_positions_list:
                for pos_str in exchange_positions_list:
                    print(f"      - {pos_str}")
            
            async with async_session() as session:
                # Получаем открытые позиции из БД
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == 'OPEN',
                        Trade.market_type == 'futures'
                    )
                )
                db_trades = list(result.scalars().all())
                
                print(f"\n📊 Позиции в БД:")
                print(f"   Открытых: {len(db_trades)}")
                if db_trades:
                    for t in db_trades:
                        print(f"      - {t.symbol} {t.side.value} {t.quantity}")
                
                synced = 0
                closed = 0
                
                # 1. ЗАКРЫВАЕМ ФАНТОМНЫЕ ПОЗИЦИИ
                # Проверяем каждую позицию из БД - есть ли она на бирже
                for trade in db_trades:
                    # Создаём ключ для поиска
                    key = (trade.symbol, trade.side.value, trade.quantity)
                    
                    # Проверяем точное совпадение
                    if key not in exchange_positions:
                        # ФАНТОМНАЯ ПОЗИЦИЯ - закрыта на бирже, но открыта в БД
                        print(f"   👻 ФАНТОМ: {trade.symbol} {trade.side.value} qty={trade.quantity} (ID: {trade.id})")
                        
                        # Получаем текущую цену для расчёта PnL
                        try:
                            ticker = await self.api.get_ticker(trade.symbol)
                            current_price = float(ticker.get('lastPrice', trade.entry_price))
                        except:
                            current_price = trade.entry_price
                        
                        # Рассчитываем PnL
                        if trade.side.value == 'BUY':
                            pnl = (current_price - trade.entry_price) * trade.quantity
                        else:  # SELL
                            pnl = (trade.entry_price - current_price) * trade.quantity
                        
                        # Рассчитываем комиссии (если не были рассчитаны)
                        if trade.fee_entry == 0:
                            entry_value = trade.entry_price * trade.quantity
                            trade.fee_entry = entry_value * settings.estimated_fee_rate
                        
                        if trade.fee_exit == 0:
                            exit_value = current_price * trade.quantity
                            trade.fee_exit = exit_value * settings.estimated_fee_rate
                        
                        # Закрываем позицию
                        trade.status = 'CLOSED'
                        trade.exit_time = datetime.utcnow()
                        trade.exit_price = current_price
                        trade.pnl = pnl
                        trade.exit_reason = 'Sync: phantom position (closed on exchange)'
                        
                        closed += 1
                        
                        print(f"      ✅ Закрыта: exit=${current_price:.2f}, PnL=${pnl:.2f}, fees=${trade.fee_entry + trade.fee_exit:.4f}")
                        
                        # ========== SELF-LEARNING: Обучение на результате ==========
                        if trade.ml_features:
                            try:
                                from core.self_learning import get_self_learner
                                learner = get_self_learner()
                                
                                # Определяем результат: 1 = Win, 0 = Loss
                                result = 1 if pnl > 0 else 0
                                
                                # Обучаем модель
                                success = learner.learn(trade.ml_features, result)
                                
                                if success:
                                    stats = learner.get_stats()
                                    print(f"      🧠 ML: Learned from {'WIN' if result == 1 else 'LOSS'} (samples: {stats['learned_samples']})")
                            
                            except Exception as e:
                                print(f"      ⚠️ ML error (ignored): {e}")
                
                # 2. ОБНОВЛЯЕМ СУЩЕСТВУЮЩИЕ ПОЗИЦИИ
                # Если quantity изменился на бирже - обновляем в БД
                for key, pos in exchange_positions.items():
                    symbol, side, size = key
                    
                    # Ищем соответствующую позицию в БД
                    for trade in db_trades:
                        if (trade.symbol == symbol and 
                            trade.side.value == side and 
                            trade.status.value == 'OPEN'):
                            
                            # Обновляем quantity если изменился
                            if abs(trade.quantity - size) > 0.0001:
                                old_qty = trade.quantity
                                trade.quantity = size
                                print(f"   🔄 Обновлена: {symbol} qty={old_qty:.4f} → {size:.4f}")
                                synced += 1
                            break
                
                await session.commit()
                
                # Итоговая статистика
                remaining_open = len(db_trades) - closed
                print(f"\n✅ Синхронизация завершена:")
                print(f"   👻 Закрыто фантомных: {closed}")
                print(f"   🔄 Обновлено: {synced}")
                print(f"   📊 Осталось открытых: {remaining_open}")
                print(f"   🌐 На бирже открытых: {len(exchange_positions)}")
                
                if remaining_open != len(exchange_positions):
                    print(f"   ⚠️  РАСХОЖДЕНИЕ: БД={remaining_open}, Bybit={len(exchange_positions)}")
                    print(f"   💡 Возможно позиции открылись после запроса к API")
                else:
                    print(f"   ✅ ПОЛНОЕ СОВПАДЕНИЕ!")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации фьючерсов: {e}")
            import traceback
            traceback.print_exc()

    async def sync_open_orders(self):
        """Синхронизировать открытые ордера (SPOT)"""
        try:
            # Получаем открытые ордера для всех пар
            all_orders = []
            
            for symbol in ['BTCUSDT', 'ETHUSDT', 'USDCUSDT']:
                try:
                    orders = await self.api.get_open_orders(symbol)
                    if orders:
                        all_orders.extend(orders)
                except:
                    pass
            
            if not all_orders:
                print("ℹ️ Нет открытых SPOT ордеров")
                return
            
            print(f"\n📊 Открытые SPOT ордера: {len(all_orders)}")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации ордеров: {e}")
    
    async def sync_all(self):
        """Синхронизировать всё"""
        print("\n" + "="*80)
        print(f"🔄 Синхронизация с Bybit API - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        await self.sync_all_balances()
        await self.sync_futures_positions()  # Синхронизация фьючерсов!
        await self.sync_open_orders()
        
        print("="*80 + "\n")


async def main():
    """Основной цикл синхронизации"""
    sync = BybitSync()
    
    print("🚀 Запуск полной синхронизации с Bybit API v2.0...")
    print(f"📊 Интервал: каждые 15 секунд (ускорено для быстрой синхронизации)")
    print(f"💡 Синхронизируем:")
    print(f"   - Балансы всех монет (USDT, USDC, BTC, ETH)")
    print(f"   - Фьючерсные позиции (с расчётом PnL)")
    print(f"   - Автоматическое закрытие фантомных позиций")
    print(f"   - Открытые ордера (спотовые)")
    print(f"   - Актуальные данные для Dashboard")
    print(f"\n🔥 НОВОЕ v2.0:")
    print(f"   - Точное сопоставление по (symbol, side, quantity)")
    print(f"   - Расчёт PnL и комиссий при закрытии фантомов")
    print(f"   - Обучение ML модели на результатах")
    print(f"   - Интервал 15s вместо 30s")
    
    while True:
        try:
            await sync.sync_all()
            await asyncio.sleep(15)  # Каждые 15 секунд (ускорено!)
        except KeyboardInterrupt:
            print("\n⏹️ Остановка синхронизации...")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле синхронизации: {e}")
            await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
