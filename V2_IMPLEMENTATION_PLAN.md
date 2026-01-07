# 🚀 Bybit Trading Bot v2.0 - Implementation Plan

## 📋 MASTER PLAN

**Start Date:** 7 января 2026  
**Initial Balance:** $100  
**Goal:** Simple, profitable trading system

---

## 🎯 Phase 1: Core System (Priority: CRITICAL)

### 1.1 Strategy Implementation ✅
- [x] Create `simple_scalper.py` with RSI Grid logic
- [x] RSI calculation (period 14)
- [x] Bollinger Bands calculation (20, 2)
- [x] Signal generation (LONG/SHORT)
- [x] Position sizing logic

### 1.2 Main Loop ✅
- [x] Create simplified `main.py`
- [x] Scan → Signal → Execute flow
- [x] Balance tracking
- [x] Position monitoring
- [ ] **Order execution integration** 🔴 NEXT
- [ ] **TP/SL management** 🔴 NEXT

### 1.3 Configuration ✅
- [x] Create `config_v2.py`
- [x] Remove ML settings
- [x] Add RSI/BB parameters
- [x] Set initial balance: $100
- [x] Set leverage: 3x
- [x] Set risk: 5% per trade

---

## 🎯 Phase 2: Order Execution (Priority: CRITICAL)

### 2.1 Futures Executor Updates
- [ ] **Review existing `futures_executor.py`** 🔴 NEXT
- [ ] **Simplify order placement logic**
- [ ] **Implement TP/SL orders**
- [ ] **Add position monitoring**
- [ ] **Test on Demo account**

### 2.2 Risk Management
- [ ] **Review `risk_manager.py`**
- [ ] **Simplify for v2 (no complex filters)**
- [ ] **Keep basic safety checks:**
  - Max positions limit (3)
  - Max loss per day
  - Balance protection

---

## 🎯 Phase 3: AI Integration (Optional)

### 3.1 AI Gateway Integration
- [ ] **Decision: Do we need AI?**
  - Option A: Pure math (RSI + BB only) ✅ RECOMMENDED
  - Option B: AI confirmation (ai.stashiq.online)

**Recommendation:** Start with pure math (Option A), add AI later if needed.

**If AI needed:**
- [ ] Create `ai_advisor.py` (simple, not complex like v1)
- [ ] Use ai.stashiq.online for signal confirmation
- [ ] API Key: `gw_hubbhzTxbxLtVnRuQ0XhsOCCjyHrvD589YfFlfRUhAg`
- [ ] Model: `gpt-4o-mini`
- [ ] Purpose: Confirm RSI signals (yes/no)

---

## 🎯 Phase 4: Telegram Bot (Priority: HIGH)

### 4.1 Review Current Bot ✅
- [x] **Check `telegram_commander.py`**
- [x] **Identify what to keep:**
  - ✅ /status - Balance and positions
  - ✅ /orders - Recent trades
  - ✅ /panic - Emergency stop
  - ❌ /brain - Remove (no AI in v2)
  - ❌ /strategy - Remove (no complex strategy)

### 4.2 Simplify Commands ✅
- [x] **Keep essential commands:**
  ```
  /start - Welcome message
  /status - Balance, positions, today's stats
  /orders - Last 10 trades
  /balance - Detailed balance info
  /panic - Emergency stop all
  ```

- [x] **Remove complex commands:**
  - /brain (no AI)
  - /strategy (no complex strategy)
  - /panic_test (not needed)

### 4.3 Notifications
- [x] **Signal notifications:**
  - "🎯 LONG BTCUSDT @ $42,150 (RSI: 28, BB: Lower)"
  - "✅ Position opened: LONG BTCUSDT"
  - "💰 Position closed: +$1.50 (+1.5%)"
  - (Will be implemented when testing on server)

---

## 🎯 Phase 5: Web Dashboard (Priority: MEDIUM)

### 5.1 Review Current Dashboard
- [ ] **Check `web/app.py`**
- [ ] **Identify what to keep:**
  - ✅ Balance display
  - ✅ Open positions
  - ✅ Trade history
  - ✅ Performance chart
  - ❌ ML status (remove)
  - ❌ AI decisions (remove)
  - ❌ Brain state (remove)

### 5.2 Simplify Dashboard
- [ ] **Keep essential pages:**
  - Main page: Balance, positions, stats
  - Trades page: History with filters
  - Performance page: Equity curve

- [ ] **Remove complex pages:**
  - /brain (no AI)
  - /ml/status (no ML)
  - Neural HUD (no AI)

### 5.3 Add v2 Specific Info
- [ ] **Strategy info panel:**
  - Current RSI values
  - BB levels
  - Last signal time
  - Signal count today

---

## 🎯 Phase 6: Database (Priority: LOW)

### 6.1 Review Schema
- [ ] **Check if current schema works for v2**
- [ ] **Keep:**
  - trades table
  - wallet_history
  - system_logs

- [ ] **Remove/Ignore:**
  - ai_decisions (not used)
  - candles (not needed for v2)

### 6.2 Clean Up
- [ ] **Optional: Archive old v1 data**
- [ ] **Keep trade history for analysis**

---

## 🎯 Phase 7: Testing (Priority: CRITICAL)

### 7.1 Unit Tests
- [ ] **Test RSI calculation**
- [ ] **Test BB calculation**
- [ ] **Test signal generation**
- [ ] **Test position sizing**

### 7.2 Integration Tests
- [ ] **Test full cycle: Scan → Signal → Execute**
- [ ] **Test TP/SL execution**
- [ ] **Test emergency stop**

### 7.3 Demo Trading
- [ ] **Deploy to server**
- [ ] **Run for 1 week**
- [ ] **Monitor:**
  - Signal quality
  - Win rate
  - Execution speed
  - Bugs/errors

---

## 🎯 Phase 8: Optimization (Priority: LOW)

### 8.1 Parameter Tuning
- [ ] **Test different RSI thresholds (25/75, 30/70, 35/65)**
- [ ] **Test different BB periods (15, 20, 25)**
- [ ] **Test different TP/SL ratios**

### 8.2 Additional Filters (Optional)
- [ ] **CHOP filter** (skip flat markets)
- [ ] **Volume filter** (skip low volume)
- [ ] **Time filter** (skip low volatility hours)

---

## 🎯 Phase 9: Production (Priority: FINAL)

### 9.1 Validation
- [ ] **100+ trades on Demo**
- [ ] **Win rate 50%+**
- [ ] **Positive ROI**
- [ ] **No critical bugs**

### 9.2 Real Trading
- [ ] **Switch to Mainnet**
- [ ] **Start with $100**
- [ ] **Monitor closely**
- [ ] **Scale up gradually**

---

## 📊 Current Status

### ✅ Completed
1. v1 system archived
2. v2 strategy created (RSI Grid)
3. Main loop created
4. Configuration created
5. Documentation complete
6. Git management done

### 🔴 Next Steps (Priority Order)

1. **Order Execution** (CRITICAL)
   - Review and simplify `futures_executor.py`
   - Implement TP/SL orders
   - Test on Demo

2. **Telegram Bot** (HIGH)
   - Simplify commands
   - Add signal notifications
   - Test notifications

3. **Testing** (CRITICAL)
   - Deploy to server
   - Run on Demo
   - Monitor performance

4. **Web Dashboard** (MEDIUM)
   - Simplify interface
   - Remove AI components
   - Add RSI/BB display

5. **Optimization** (LOW)
   - Parameter tuning
   - Additional filters
   - Performance analysis

---

## 🎯 Success Criteria

### Week 1
- [ ] Bot running on Demo
- [ ] 20+ trades executed
- [ ] No critical bugs
- [ ] Telegram notifications working

### Week 2
- [ ] 50+ trades executed
- [ ] Win rate measured
- [ ] Performance analyzed
- [ ] Bugs fixed

### Month 1
- [ ] 100+ trades executed
- [ ] Win rate 50%+
- [ ] ROI positive
- [ ] Ready for Real Trading

---

## 💡 Key Decisions

### AI Integration: NO (for now)
**Reason:** Keep it simple, pure math first. Add AI later if needed.

### Telegram Bot: SIMPLIFY
**Reason:** Remove AI commands, keep essential monitoring.

### Web Dashboard: SIMPLIFY
**Reason:** Remove ML/AI displays, keep core metrics.

### Database: KEEP AS IS
**Reason:** Current schema works fine for v2.

---

## 🚀 Let's Start!

**Next Action:** Review and update `futures_executor.py` for v2

**Command:**
```bash
# Review current executor
cat Bybit_Trader/core/executors/futures_executor.py
```

---

**Updated:** 7 января 2026, 23:00 UTC  
**Status:** 🟢 READY TO START  
**Phase:** 2.1 - Order Execution
