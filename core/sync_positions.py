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
        """Синхронизировать фьючерсные позиции с биржей"""
        try:
            # Получаем реальные позиции с биржи
            positions = await self.api.get_positions()
            
            # Фильтруем только открытые (size > 0)
            exchange_positions = {}
            for pos in positions:
                size = float(pos.get('size', 0))
                if size > 0:
                    symbol = pos.get('symbol', '')
                    side = 'BUY' if pos.get('side') == 'Buy' else 'SELL'
                    exchange_positions[symbol] = {
                        'side': side,
                        'size': size,
                        'entry_price': float(pos.get('entry_price', 0) or pos.get('avgPrice', 0)),
                        'leverage': pos.get('leverage', '1')
                    }
            
            print(f"\n📊 Фьючерсные позиции на бирже: {len(exchange_positions)}")
            
            async with async_session() as session:
                # Получаем открытые позиции из БД
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == 'OPEN',
                        Trade.market_type == 'futures'
                    )
                )
                db_trades = list(result.scalars().all())
                db_symbols = {t.symbol: t for t in db_trades}
                
                synced = 0
                closed = 0
                added = 0
                
                # 1. Закрываем позиции в БД которых нет на бирже
                for trade in db_trades:
                    if trade.symbol not in exchange_positions:
                        trade.status = 'CLOSED'
                        trade.exit_time = datetime.utcnow()
                        trade.exit_price = trade.entry_price  # Примерно
                        trade.exit_reason = 'Sync: closed on exchange'
                        print(f"   ❌ Закрыта в БД: {trade.symbol} (нет на бирже)")
                        closed += 1
                    else:
                        # Проверяем совпадение стороны
                        ex_pos = exchange_positions[trade.symbol]
                        if trade.side.value != ex_pos['side']:
                            # Сторона изменилась - закрываем старую
                            trade.status = 'CLOSED'
                            trade.exit_time = datetime.utcnow()
                            trade.exit_price = trade.entry_price
                            trade.exit_reason = f'Sync: reversed to {ex_pos["side"]}'
                            print(f"   🔄 Реверс: {trade.symbol} {trade.side.value} -> {ex_pos['side']}")
                            closed += 1
                
                # 2. Добавляем позиции с биржи которых нет в БД
                for symbol, pos in exchange_positions.items():
                    # Проверяем есть ли уже открытая позиция с такой стороной
                    existing = None
                    for t in db_trades:
                        if t.symbol == symbol and t.side.value == pos['side'] and t.status.value == 'OPEN':
                            existing = t
                            break
                    
                    if not existing:
                        from database.models import TradeSide, TradeStatus
                        new_trade = Trade(
                            symbol=symbol,
                            side=TradeSide.BUY if pos['side'] == 'BUY' else TradeSide.SELL,
                            entry_price=pos['entry_price'],
                            quantity=pos['size'],
                            status=TradeStatus.OPEN,
                            entry_time=datetime.utcnow(),
                            market_type='futures',
                            stop_loss=pos['entry_price'] * (1.02 if pos['side'] == 'SELL' else 0.985),
                            take_profit=pos['entry_price'] * (0.97 if pos['side'] == 'SELL' else 1.03),
                            ai_model='Sync',
                            ai_risk_score=5,
                            ai_confidence=0.5,
                            ai_reasoning=f'Synced from exchange (leverage: {pos["leverage"]}x)'
                        )
                        session.add(new_trade)
                        print(f"   ➕ Добавлена: {symbol} {pos['side']} {pos['size']} @ ${pos['entry_price']:.2f}")
                        added += 1
                    else:
                        # Обновляем quantity если изменился
                        if abs(existing.quantity - pos['size']) > 0.0001:
                            existing.quantity = pos['size']
                            print(f"   🔄 Обновлена: {symbol} qty={pos['size']}")
                            synced += 1
                
                await session.commit()
                
                if closed + added + synced > 0:
                    print(f"✅ Синхронизация: +{added} добавлено, -{closed} закрыто, ~{synced} обновлено")
                else:
                    print(f"✅ БД синхронизирована с биржей")
                
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
