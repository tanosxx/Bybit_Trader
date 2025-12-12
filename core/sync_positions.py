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
        
        PHANTOM KILLER v3.0 - Принудительный ликвидатор:
        1. Получаем позиции с биржи (только открытые size > 0)
        2. Получаем открытые позиции из БД
        3. НАХОДИМ ФАНТОМОВ:
           - Позиции на бирже, которых НЕТ в БД (или они закрыты)
           - Позиции в БД, которых НЕТ на бирже
        4. ЛИКВИДИРУЕМ ФАНТОМОВ:
           - Закрываем на бирже через Market ордер (reduce_only=True)
           - Обновляем БД
           - Рассчитываем PnL и комиссии
           - Обучаем ML модель
        """
        try:
            # ========== ШАГ 1: ПОЛУЧАЕМ ПОЗИЦИИ С БИРЖИ ==========
            all_positions = await self.api.get_positions()
            
            # Создаём словарь открытых позиций на бирже
            # Ключ: symbol (без учёта side/qty для обнаружения фантомов)
            exchange_positions_by_symbol = {}
            exchange_positions_list = []
            
            for pos in all_positions:
                symbol = pos.get('symbol', '')
                size = float(pos.get('size', 0))
                
                if size > 0:
                    # Открытая позиция
                    side = 'BUY' if pos.get('side') == 'Buy' else 'SELL'
                    entry_price = float(pos.get('avgPrice', 0) or pos.get('entry_price', 0))
                    
                    exchange_positions_by_symbol[symbol] = {
                        'symbol': symbol,
                        'side': side,
                        'size': size,
                        'entry_price': entry_price,
                        'leverage': pos.get('leverage', '1'),
                        'unrealised_pnl': float(pos.get('unrealisedPnl', 0))
                    }
                    exchange_positions_list.append(f"{symbol} {side} {size}")
            
            print(f"\n📊 Фьючерсные позиции на бирже:")
            print(f"   Открытых: {len(exchange_positions_by_symbol)}")
            if exchange_positions_list:
                for pos_str in exchange_positions_list:
                    print(f"      - {pos_str}")
            
            # ========== ШАГ 2: ПОЛУЧАЕМ ПОЗИЦИИ ИЗ БД ==========
            async with async_session() as session:
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
                
                # Создаём словарь позиций из БД по символу
                db_positions_by_symbol = {}
                for trade in db_trades:
                    db_positions_by_symbol[trade.symbol] = trade
                
                # ========== ШАГ 3: PHANTOM KILLER - ЛИКВИДАЦИЯ ФАНТОМОВ ==========
                phantoms_killed = 0
                db_phantoms_closed = 0
                
                # 3A. ФАНТОМЫ НА БИРЖЕ (есть на бирже, но НЕТ в БД)
                print(f"\n👻 PHANTOM KILLER: Поиск фантомов на бирже...")
                
                for symbol, pos in exchange_positions_by_symbol.items():
                    # Проверяем: есть ли эта позиция в БД?
                    if symbol not in db_positions_by_symbol:
                        # ФАНТОМ! Позиция на бирже, но нет в БД
                        print(f"\n   🔥 ФАНТОМ ОБНАРУЖЕН: {symbol} {pos['side']} qty={pos['size']}")
                        print(f"      Причина: Позиция на бирже, но НЕТ в БД")
                        
                        # ЛИКВИДАЦИЯ: Закрываем на бирже
                        try:
                            # Определяем сторону закрытия
                            close_side = 'Sell' if pos['side'] == 'BUY' else 'Buy'
                            
                            print(f"      💀 Отправка ордера на ликвидацию...")
                            print(f"         Symbol: {symbol}")
                            print(f"         Side: {close_side} (закрываем {pos['side']})")
                            print(f"         Qty: {pos['size']}")
                            print(f"         Type: Market (reduce_only=True)")
                            
                            # Отправляем Market ордер на закрытие
                            order_result = await self.api.place_futures_order(
                                symbol=symbol,
                                side=close_side,
                                order_type='Market',
                                qty=pos['size'],
                                reduce_only=True  # КРИТИЧНО! Только закрытие, не открытие встречной
                            )
                            
                            print(f"      ✅ ФАНТОМ ЛИКВИДИРОВАН на бирже!")
                            print(f"         Order ID: {order_result.get('order_id', 'N/A')}")
                            print(f"         Status: {order_result.get('status', 'Unknown')}")
                            
                            phantoms_killed += 1
                            
                            # Создаём запись в БД о ликвидации фантома
                            from database.models import TradeSide
                            phantom_trade = Trade(
                                symbol=symbol,
                                side=TradeSide.BUY if pos['side'] == 'BUY' else TradeSide.SELL,
                                entry_price=pos['entry_price'],
                                quantity=pos['size'],
                                entry_time=datetime.utcnow(),
                                exit_time=datetime.utcnow(),
                                exit_price=pos['entry_price'],  # Примерная цена
                                pnl=pos['unrealised_pnl'],
                                fee_entry=0.0,
                                fee_exit=0.0,
                                status='CLOSED',
                                market_type='futures',
                                exit_reason='Phantom Killer: Liquidated phantom position on exchange',
                                leverage=int(pos['leverage'])
                            )
                            session.add(phantom_trade)
                            
                        except Exception as e:
                            print(f"      ❌ ОШИБКА ЛИКВИДАЦИИ: {e}")
                            print(f"         Фантом остался на бирже!")
                            import traceback
                            traceback.print_exc()
                
                # 3B. ФАНТОМЫ В БД (есть в БД, но НЕТ на бирже)
                print(f"\n👻 PHANTOM KILLER: Поиск фантомов в БД...")
                
                for trade in db_trades:
                    # Проверяем: есть ли эта позиция на бирже?
                    if trade.symbol not in exchange_positions_by_symbol:
                        # ФАНТОМ! Позиция в БД, но нет на бирже
                        print(f"\n   👻 ФАНТОМ В БД: {trade.symbol} {trade.side.value} qty={trade.quantity} (ID: {trade.id})")
                        print(f"      Причина: Позиция в БД, но НЕТ на бирже (уже закрыта)")
                        
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
                        
                        # Рассчитываем комиссии
                        if trade.fee_entry == 0:
                            entry_value = trade.entry_price * trade.quantity
                            trade.fee_entry = entry_value * settings.estimated_fee_rate
                        
                        if trade.fee_exit == 0:
                            exit_value = current_price * trade.quantity
                            trade.fee_exit = exit_value * settings.estimated_fee_rate
                        
                        # Закрываем в БД
                        trade.status = 'CLOSED'
                        trade.exit_time = datetime.utcnow()
                        trade.exit_price = current_price
                        trade.pnl = pnl
                        trade.exit_reason = 'Phantom Killer: Position already closed on exchange'
                        
                        db_phantoms_closed += 1
                        
                        print(f"      ✅ Закрыт в БД: exit=${current_price:.2f}, PnL=${pnl:.2f}, fees=${trade.fee_entry + trade.fee_exit:.4f}")
                        
                        # ========== SELF-LEARNING: Обучение на результате ==========
                        if trade.ml_features:
                            try:
                                from core.self_learning import get_self_learner
                                learner = get_self_learner()
                                
                                # Определяем результат: 1 = Win, 0 = Loss
                                ml_result = 1 if pnl > 0 else 0
                                
                                # Обучаем модель
                                success = learner.learn(trade.ml_features, ml_result)
                                
                                if success:
                                    stats = learner.get_stats()
                                    print(f"      🧠 ML: Learned from {'WIN' if ml_result == 1 else 'LOSS'} (samples: {stats['learned_samples']})")
                            
                            except Exception as e:
                                print(f"      ⚠️ ML error (ignored): {e}")
                
                await session.commit()
                
                # ========== ИТОГОВАЯ СТАТИСТИКА ==========
                remaining_db = len(db_trades) - db_phantoms_closed
                remaining_exchange = len(exchange_positions_by_symbol) - phantoms_killed
                
                print(f"\n" + "="*80)
                print(f"✅ PHANTOM KILLER: Синхронизация завершена")
                print(f"="*80)
                print(f"   💀 Ликвидировано на бирже: {phantoms_killed}")
                print(f"   👻 Закрыто в БД: {db_phantoms_closed}")
                print(f"   📊 Осталось в БД: {remaining_db}")
                print(f"   🌐 Осталось на бирже: {remaining_exchange}")
                
                if remaining_db != remaining_exchange:
                    print(f"   ⚠️  РАСХОЖДЕНИЕ: БД={remaining_db}, Bybit={remaining_exchange}")
                    print(f"   💡 Возможно позиции открылись после запроса к API")
                else:
                    print(f"   ✅ ПОЛНОЕ СОВПАДЕНИЕ!")
                print(f"="*80)
                
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
    
    print("🚀 Запуск PHANTOM KILLER v3.0 - Принудительный ликвидатор...")
    print(f"📊 Интервал: каждые 15 секунд")
    print(f"💡 Синхронизируем:")
    print(f"   - Балансы всех монет (USDT, USDC, BTC, ETH)")
    print(f"   - Фьючерсные позиции (с расчётом PnL)")
    print(f"   - Открытые ордера (спотовые)")
    print(f"   - Актуальные данные для Dashboard")
    print(f"\n🔥 PHANTOM KILLER v3.0:")
    print(f"   💀 ЛИКВИДАЦИЯ ФАНТОМОВ НА БИРЖЕ:")
    print(f"      - Обнаружение позиций на бирже без записи в БД")
    print(f"      - Автоматическое закрытие через Market ордер (reduce_only=True)")
    print(f"      - Создание записи о ликвидации в БД")
    print(f"   👻 ЗАКРЫТИЕ ФАНТОМОВ В БД:")
    print(f"      - Обнаружение позиций в БД, которых нет на бирже")
    print(f"      - Расчёт PnL и комиссий")
    print(f"      - Обучение ML модели на результатах")
    print(f"   ✅ ПОЛНАЯ СИНХРОНИЗАЦИЯ: БД ↔ Биржа")
    
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
