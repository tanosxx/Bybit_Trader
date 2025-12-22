// ============================================
// BYBIT TRADING BOT - PREMIUM DASHBOARD
// JavaScript Controller
// ============================================

// Global State
let allTrades = [];
let currentPage = 1;
const perPage = 10;

// ============================================
// UTILITY FUNCTIONS
// ============================================

function fmt(value, decimals = 2) {
    if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
        return '0.00';
    }
    return Number(value).toFixed(decimals);
}

function safeStr(value, fallback = 'N/A') {
    return (value !== null && value !== undefined && value !== '') ? String(value) : fallback;
}

function adjustTime(timeStr) {
    if (!timeStr || timeStr === 'N/A') return timeStr;
    try {
        const date = new Date(timeStr);
        date.setHours(date.getHours() + 5); // +5 hours for Russia
        return date.toLocaleString('ru-RU');
    } catch(e) {
        return timeStr;
    }
}

function formatCurrency(value) {
    return '$' + fmt(value);
}

function formatPercent(value, decimals = 1) {
    return fmt(value, decimals) + '%';
}

// ============================================
// DATA FETCHING
// ============================================

function fetchData() {
    fetch('/api/data')
        .then(response => {
            if (!response.ok) {
                throw new Error('API Error ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            updateUI(data);
        })
        .catch(error => {
            console.error('Fetch error:', error);
            showError('balances-container', error.message);
        });
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="error">⚠️ ${message}</div>`;
    }
}

// ============================================
// UI UPDATE FUNCTIONS
// ============================================

function updateUI(data) {
    updateBalance(data.balance || {});
    updateStats(data.stats || {});
    updateTierInfo(data.tier_info || {});
    updateBalances(data.balance?.balances || []);
    updateTrades(data.closed_trades || []);
    updateLogs(data.logs || []);
    updateTimestamp(data.timestamp);
}

function updateBalance(balance) {
    const totalBalance = balance.total_usdt || 0;
    const initialBalance = balance.initial_balance || 100;
    const pnl = balance.total_pnl || 0;
    const pnlPercent = initialBalance > 0 ? (pnl / initialBalance) * 100 : 0;
    
    // Update hero balance
    document.getElementById('total-balance').textContent = formatCurrency(totalBalance);
    document.getElementById('initial-balance').textContent = formatCurrency(initialBalance);
    
    // Update balance change
    const changeEl = document.getElementById('balance-change');
    changeEl.textContent = (pnlPercent >= 0 ? '+' : '') + formatPercent(pnlPercent);
    changeEl.className = 'balance-change ' + (pnlPercent >= 0 ? 'positive' : 'negative');
}

function updateStats(stats) {
    document.getElementById('total-trades').textContent = stats.total_trades || 0;
    document.getElementById('winrate').textContent = formatPercent(stats.winrate || 0);
    
    const pnl = stats.total_pnl || 0;
    const pnlEl = document.getElementById('total-pnl');
    pnlEl.textContent = formatCurrency(pnl);
    pnlEl.className = 'metric-value ' + (pnl >= 0 ? 'positive' : 'negative');
}

function updateTierInfo(tierInfo) {
    const tierEl = document.getElementById('strategy-tier');
    
    if (tierInfo.enabled) {
        const tierText = `${tierInfo.current_tier} (${tierInfo.active_pairs.join(', ')})`;
        const subText = `Max: ${tierInfo.max_positions} | Risk: ${(tierInfo.risk_per_trade * 100).toFixed(0)}%`;
        tierEl.innerHTML = `${tierText}<br><span style="font-size: 0.7rem; color: var(--text-muted);">${subText}</span>`;
    } else {
        tierEl.textContent = 'N/A';
    }
}

function updateBalances(balances) {
    const container = document.getElementById('balances-container');
    
    if (balances.length === 0) {
        container.innerHTML = '<div class="loading">No balances available</div>';
        return;
    }
    
    let html = '';
    balances.forEach(balance => {
        const change = balance.change_amount || 0;
        const changeClass = change >= 0 ? 'positive' : 'negative';
        
        html += `
            <div class="balance-card">
                <div class="balance-coin">${safeStr(balance.coin)}</div>
                <div class="balance-row">
                    <span class="balance-label">Quantity:</span>
                    <span>${fmt(balance.total, 6)}</span>
                </div>
                <div class="balance-row">
                    <span class="balance-label">Price:</span>
                    <span>${formatCurrency(balance.current_price)}</span>
                </div>
                <div class="balance-row">
                    <span class="balance-label">Value:</span>
                    <span>${formatCurrency(balance.usdt_value)}</span>
                </div>
                <div class="balance-row">
                    <span class="balance-label">Change:</span>
                    <span class="${changeClass}">${change >= 0 ? '+' : ''}${fmt(change, 6)}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function updateTrades(trades) {
    allTrades = trades;
    currentPage = 1;
    renderTrades();
}

function renderTrades() {
    const tbody = document.getElementById('trades-body');
    const totalPages = Math.max(1, Math.ceil(allTrades.length / perPage));
    
    if (currentPage > totalPages) {
        currentPage = totalPages;
    }
    
    const start = (currentPage - 1) * perPage;
    const pageTrades = allTrades.slice(start, start + perPage);
    
    if (pageTrades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No trades available</td></tr>';
        return;
    }
    
    let html = '';
    pageTrades.forEach(trade => {
        const pnl = trade.pnl || 0;
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        const sideClass = trade.side === 'BUY' ? 'badge-long' : 'badge-short';
        const sideText = trade.side === 'BUY' ? 'LONG' : 'SHORT';
        
        html += `
            <tr>
                <td>${safeStr(trade.symbol)}</td>
                <td><span class="badge ${sideClass}">${sideText}</span></td>
                <td>${formatCurrency(trade.entry_price)}</td>
                <td>${formatCurrency(trade.exit_price)}</td>
                <td>${fmt(trade.quantity, 6)}</td>
                <td class="${pnlClass}">${formatCurrency(pnl)}</td>
                <td class="${pnlClass}">${formatPercent(trade.pnl_pct || 0)}</td>
                <td>${adjustTime(trade.exit_time)}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    
    // Update pagination
    document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prev-btn').disabled = currentPage <= 1;
    document.getElementById('next-btn').disabled = currentPage >= totalPages;
}

function updateLogs(logs) {
    const container = document.getElementById('logs-container');
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="loading">No logs available</div>';
        return;
    }
    
    let html = '';
    const displayLogs = logs.slice(0, 50); // Show last 50 logs
    
    displayLogs.forEach(log => {
        const level = safeStr(log.level, 'INFO');
        const time = safeStr(log.time, '--');
        const component = safeStr(log.component, 'System');
        const message = safeStr(log.message, '');
        
        html += `
            <div class="log-entry log-${level}">
                [${time}] [${component}] ${message}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function updateTimestamp(timestamp) {
    const el = document.getElementById('last-update');
    if (el) {
        el.textContent = 'Last update: ' + adjustTime(timestamp);
    }
}

// ============================================
// PAGINATION CONTROLS
// ============================================

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderTrades();
    }
}

function nextPage() {
    const totalPages = Math.ceil(allTrades.length / perPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderTrades();
    }
}

// ============================================
// INITIALIZATION
// ============================================

// Initial fetch
fetchData();

// Auto-refresh every 5 seconds
setInterval(fetchData, 5000);

// Log initialization
console.log('🤖 Bybit Trading Bot Dashboard initialized');
