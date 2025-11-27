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
    
    async def sync_open_orders(self):
        """Синхронизировать открытые ордера"""
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
            
            # Также получаем без фильтра
            try:
                orders = await self.api.get_open_orders()
                if orders:
                    all_orders.extend(orders)
            except:
                pass
            
            if not all_orders:
                print("ℹ️ Нет открытых ордеров")
                return
            
            print(f"\n📊 Открытые ордера: {len(all_orders)}")
            
            async with async_session() as session:
                # Получаем текущие открытые позиции из БД
                result = await session.execute(
                    select(Trade).where(Trade.status == 'OPEN')
                )
                db_trades = {(t.symbol, t.side): t for t in result.scalars().all()}
                
                synced_count = 0
                
                # Синхронизируем каждый ордер
                for order in all_orders:
                    try:
                        symbol = order.get('symbol', '')
                        side = order.get('side', '')  # Buy/Sell
                        qty = float(order.get('qty', 0))
                        price = float(order.get('price', 0))
                        order_id = order.get('orderId', '')
                        
                        if qty == 0 or not symbol:
                            continue
                        
                        # Нормализуем side
                        side_normalized = 'BUY' if side == 'Buy' else 'SELL'
                        
                        key = (symbol, side_normalized)
                        
                        # Проверяем есть ли в БД
                        if key in db_trades:
                            # Обновляем существующую
                            trade = db_trades[key]
                            trade.quantity = qty
                            trade.entry_price = price
                            print(f"   🔄 {symbol} {side_normalized} {qty:.4f} @ ${price:.2f}")
                        else:
                            # Создаем новую
                            new_trade = Trade(
                                symbol=symbol,
                                side=side_normalized,
                                entry_price=price,
                                quantity=qty,
                                status='OPEN',
                                entry_time=datetime.utcnow(),
                                stop_loss=price * 1.02 if side_normalized == 'SELL' else price * 0.98,
                                take_profit=price * 0.97 if side_normalized == 'SELL' else price * 1.03,
                                ai_model='Manual',
                                ai_risk_score=5,
                                ai_confidence=0.5,
                                ai_reasoning=f'Imported from Bybit (Order ID: {order_id})'
                            )
                            session.add(new_trade)
                            print(f"   ➕ {symbol} {side_normalized} {qty:.4f} @ ${price:.2f}")
                        
                        synced_count += 1
                        
                    except Exception as e:
                        print(f"   ⚠️ Ошибка обработки ордера: {e}")
                        continue
                
                await session.commit()
                print(f"✅ Синхронизировано {synced_count} ордеров")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации ордеров: {e}")
            import traceback
            traceback.print_exc()
    
    async def sync_all(self):
        """Синхронизировать всё"""
        print("\n" + "="*80)
        print(f"🔄 Синхронизация с Bybit API - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        await self.sync_all_balances()
        await self.sync_open_orders()
        
        print("="*80 + "\n")


async def main():
    """Основной цикл синхронизации"""
    sync = BybitSync()
    
    print("🚀 Запуск полной синхронизации с Bybit API...")
    print(f"📊 Интервал: каждые 30 секунд")
    print(f"💡 Синхронизируем:")
    print(f"   - Балансы всех монет (USDT, USDC, BTC, ETH)")
    print(f"   - Открытые ордера (спотовые)")
    print(f"   - Актуальные данные для Dashboard")
    
    while True:
        try:
            await sync.sync_all()
            await asyncio.sleep(30)  # Каждые 30 секунд
        except KeyboardInterrupt:
            print("\n⏹️ Остановка синхронизации...")
            break
        except Exception as e:
            print(f"❌ Ошибка в цикле синхронизации: {e}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
