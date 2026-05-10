-- Positions across all asset classes
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_class TEXT NOT NULL CHECK(asset_class IN ('stock', 'crypto', 'forex', 'options', 'sports_card')),
    symbol TEXT NOT NULL,
    exchange TEXT,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_class, symbol, exchange)
);

-- Agent-generated recommendations
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_type TEXT NOT NULL CHECK(decision_type IN ('buy', 'sell', 'hold', 'arbitrage')),
    asset_class TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    quantity REAL,
    action_price REAL,
    confidence REAL,
    reasoning TEXT NOT NULL,
    risk_level TEXT CHECK(risk_level IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'expired', 'executed')),
    timeout_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    human_approved BOOLEAN,
    execution_result TEXT
);

-- Trade execution log
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER REFERENCES decisions(id),
    symbol TEXT NOT NULL,
    exchange TEXT,
    side TEXT CHECK(side IN ('buy', 'sell')),
    quantity REAL NOT NULL,
    price REAL,
    commission REAL,
    executed_at DATETIME,
    broker TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Interactive chat messages per decision
CREATE TABLE IF NOT EXISTS decision_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER REFERENCES decisions(id),
    role TEXT CHECK(role IN ('human', 'agent')),
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sports card portfolio
CREATE TABLE IF NOT EXISTS sports_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    set_name TEXT NOT NULL,
    grade TEXT,
    grader TEXT CHECK(grader IN ('PSA', 'BGS', 'CGC', 'ungraded')),
    purchase_price REAL,
    current_estimated_value REAL,
    market_source TEXT,
    card_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Daily reports
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE NOT NULL UNIQUE,
    overnight_summary TEXT,
    critical_events TEXT,
    investment_windows TEXT,
    risk_metrics TEXT,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent activity log
CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Market data cache
CREATE TABLE IF NOT EXISTS market_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT,
    data_type TEXT NOT NULL,
    raw_data TEXT NOT NULL,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange, data_type)
);

-- Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_class TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_class, symbol, exchange)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_timeout ON decisions(timeout_at);
CREATE INDEX IF NOT EXISTS idx_trades_decision ON trades(decision_id);
CREATE INDEX IF NOT EXISTS idx_market_cache_symbol ON market_cache(symbol, exchange);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent_name, created_at);

-- Portfolio P&L snapshots
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_value REAL,
    positions_json TEXT,
    allocation_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dispatcher pipeline event audit trail
CREATE TABLE IF NOT EXISTS dispatcher_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    alert_source TEXT,
    decision_id INTEGER REFERENCES decisions(id),
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Telegram message log (inbound + outbound)
CREATE TABLE IF NOT EXISTS telegram_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT CHECK(direction IN ('inbound', 'outbound')),
    chat_id TEXT,
    message_id TEXT,
    text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);