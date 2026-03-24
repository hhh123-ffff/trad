-- Quant Trading Platform Database Schema
-- Target: PostgreSQL 14+
-- Phase 1 baseline schema

BEGIN;

-- Keep timestamp updates consistent across mutable tables.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Master stock metadata.
CREATE TABLE IF NOT EXISTS stocks (
  id BIGSERIAL PRIMARY KEY,
  symbol VARCHAR(16) NOT NULL UNIQUE,
  name VARCHAR(64) NOT NULL,
  exchange VARCHAR(16) NOT NULL,
  industry VARCHAR(64),
  listing_date DATE,
  status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_stocks_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DELISTED'))
);

CREATE TRIGGER trg_stocks_updated_at
BEFORE UPDATE ON stocks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Daily OHLCV bars.
CREATE TABLE IF NOT EXISTS prices (
  id BIGSERIAL PRIMARY KEY,
  stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  trade_date DATE NOT NULL,
  open NUMERIC(12, 4) NOT NULL,
  high NUMERIC(12, 4) NOT NULL,
  low NUMERIC(12, 4) NOT NULL,
  close NUMERIC(12, 4) NOT NULL,
  adj_close NUMERIC(12, 4),
  volume BIGINT NOT NULL,
  amount NUMERIC(18, 2),
  source VARCHAR(32) NOT NULL DEFAULT 'AKSHARE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_prices_stock_date UNIQUE (stock_id, trade_date),
  CONSTRAINT ck_prices_price_non_negative CHECK (
    open >= 0 AND high >= 0 AND low >= 0 AND close >= 0
  ),
  CONSTRAINT ck_prices_volume_non_negative CHECK (volume >= 0)
);

CREATE INDEX IF NOT EXISTS idx_prices_trade_date ON prices(trade_date);
CREATE INDEX IF NOT EXISTS idx_prices_stock_trade_date ON prices(stock_id, trade_date);

-- Optional normalized fundamentals for future factor expansion.
CREATE TABLE IF NOT EXISTS fundamentals (
  id BIGSERIAL PRIMARY KEY,
  stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  report_date DATE NOT NULL,
  pe_ttm NUMERIC(12, 4),
  pb NUMERIC(12, 4),
  roe NUMERIC(12, 4),
  revenue_yoy NUMERIC(12, 4),
  net_profit_yoy NUMERIC(12, 4),
  source VARCHAR(32) NOT NULL DEFAULT 'RESERVED',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_fundamentals_stock_report UNIQUE (stock_id, report_date)
);

CREATE INDEX IF NOT EXISTS idx_fundamentals_report_date ON fundamentals(report_date);

-- Daily factor snapshot per stock.
CREATE TABLE IF NOT EXISTS factors (
  id BIGSERIAL PRIMARY KEY,
  stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  trade_date DATE NOT NULL,
  momentum_20 NUMERIC(12, 6),
  momentum_60 NUMERIC(12, 6),
  volume_factor NUMERIC(12, 6),
  volatility_20 NUMERIC(12, 6),
  fundamental_factor NUMERIC(12, 6),
  total_score NUMERIC(12, 6),
  factor_version VARCHAR(32) NOT NULL DEFAULT 'v1',
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_factors_stock_date_version UNIQUE (stock_id, trade_date, factor_version)
);

CREATE INDEX IF NOT EXISTS idx_factors_trade_date ON factors(trade_date);
CREATE INDEX IF NOT EXISTS idx_factors_trade_date_score ON factors(trade_date, total_score DESC);

-- Strategy outputs.
CREATE TABLE IF NOT EXISTS signals (
  id BIGSERIAL PRIMARY KEY,
  trade_date DATE NOT NULL,
  stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  strategy_name VARCHAR(64) NOT NULL,
  action VARCHAR(8) NOT NULL,
  score NUMERIC(12, 6),
  target_weight NUMERIC(8, 6),
  reason TEXT,
  status VARCHAR(16) NOT NULL DEFAULT 'NEW',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_signals_date_stock_strategy UNIQUE (trade_date, stock_id, strategy_name),
  CONSTRAINT ck_signals_action CHECK (action IN ('BUY', 'SELL', 'HOLD')),
  CONSTRAINT ck_signals_status CHECK (status IN ('NEW', 'EXECUTED', 'CANCELLED')),
  CONSTRAINT ck_signals_target_weight CHECK (target_weight IS NULL OR (target_weight >= 0 AND target_weight <= 1))
);

CREATE INDEX IF NOT EXISTS idx_signals_trade_date ON signals(trade_date);
CREATE INDEX IF NOT EXISTS idx_signals_trade_date_action ON signals(trade_date, action);

CREATE TRIGGER trg_signals_updated_at
BEFORE UPDATE ON signals
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Simulated order records.
CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  account_name VARCHAR(64) NOT NULL,
  signal_id BIGINT REFERENCES signals(id) ON DELETE SET NULL,
  stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE RESTRICT,
  order_date DATE NOT NULL,
  side VARCHAR(8) NOT NULL,
  order_type VARCHAR(16) NOT NULL DEFAULT 'SIM',
  price NUMERIC(12, 4) NOT NULL,
  quantity INTEGER NOT NULL,
  filled_quantity INTEGER NOT NULL DEFAULT 0,
  fee NUMERIC(18, 2) NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_orders_side CHECK (side IN ('BUY', 'SELL')),
  CONSTRAINT ck_orders_status CHECK (status IN ('PENDING', 'FILLED', 'PARTIAL', 'CANCELLED', 'REJECTED')),
  CONSTRAINT ck_orders_quantity_positive CHECK (quantity > 0),
  CONSTRAINT ck_orders_filled_quantity_valid CHECK (filled_quantity >= 0 AND filled_quantity <= quantity),
  CONSTRAINT ck_orders_price_non_negative CHECK (price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_orders_account_date ON orders(account_name, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_stock_date ON orders(stock_id, order_date);

CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Daily position snapshot.
CREATE TABLE IF NOT EXISTS positions (
  id BIGSERIAL PRIMARY KEY,
  account_name VARCHAR(64) NOT NULL,
  stock_id BIGINT NOT NULL REFERENCES stocks(id) ON DELETE RESTRICT,
  snapshot_date DATE NOT NULL,
  quantity INTEGER NOT NULL,
  available_quantity INTEGER NOT NULL,
  avg_cost NUMERIC(12, 4) NOT NULL,
  last_price NUMERIC(12, 4) NOT NULL,
  market_value NUMERIC(18, 2) NOT NULL,
  unrealized_pnl NUMERIC(18, 2) NOT NULL,
  unrealized_pnl_pct NUMERIC(12, 6) NOT NULL,
  weight NUMERIC(8, 6) NOT NULL,
  stop_loss_price NUMERIC(12, 4),
  status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_positions_account_stock_date UNIQUE (account_name, stock_id, snapshot_date),
  CONSTRAINT ck_positions_quantity_non_negative CHECK (quantity >= 0),
  CONSTRAINT ck_positions_available_quantity_valid CHECK (available_quantity >= 0 AND available_quantity <= quantity),
  CONSTRAINT ck_positions_weight_valid CHECK (weight >= 0 AND weight <= 1),
  CONSTRAINT ck_positions_status CHECK (status IN ('OPEN', 'CLOSED'))
);

CREATE INDEX IF NOT EXISTS idx_positions_account_date ON positions(account_name, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_positions_snapshot_date ON positions(snapshot_date);

CREATE TRIGGER trg_positions_updated_at
BEFORE UPDATE ON positions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Daily portfolio snapshot for one account.
CREATE TABLE IF NOT EXISTS portfolio (
  id BIGSERIAL PRIMARY KEY,
  account_name VARCHAR(64) NOT NULL,
  as_of_date DATE NOT NULL,
  cash NUMERIC(18, 2) NOT NULL,
  market_value NUMERIC(18, 2) NOT NULL,
  total_asset NUMERIC(18, 2) NOT NULL,
  daily_pnl NUMERIC(18, 2) NOT NULL,
  cumulative_return NUMERIC(12, 6) NOT NULL,
  nav NUMERIC(12, 6) NOT NULL,
  position_ratio NUMERIC(8, 6) NOT NULL,
  max_drawdown NUMERIC(12, 6) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_portfolio_account_date UNIQUE (account_name, as_of_date),
  CONSTRAINT ck_portfolio_non_negative CHECK (
    cash >= 0 AND market_value >= 0 AND total_asset >= 0 AND nav >= 0
  ),
  CONSTRAINT ck_portfolio_position_ratio CHECK (position_ratio >= 0 AND position_ratio <= 1)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_account_date ON portfolio(account_name, as_of_date);

-- Risk alerts and state logs.
CREATE TABLE IF NOT EXISTS risk_logs (
  id BIGSERIAL PRIMARY KEY,
  risk_date DATE NOT NULL,
  account_name VARCHAR(64) NOT NULL,
  risk_type VARCHAR(32) NOT NULL,
  level VARCHAR(16) NOT NULL,
  message TEXT NOT NULL,
  metric_value NUMERIC(18, 6),
  threshold_value NUMERIC(18, 6),
  resolved BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_risk_logs_level CHECK (level IN ('INFO', 'WARNING', 'CRITICAL')),
  CONSTRAINT ck_risk_logs_type CHECK (risk_type IN (
    'POSITION_LIMIT',
    'STOP_LOSS',
    'MAX_DRAWDOWN',
    'EXPOSURE_LIMIT',
    'DATA_QUALITY'
  ))
);

CREATE INDEX IF NOT EXISTS idx_risk_logs_date_level ON risk_logs(risk_date, level);
CREATE INDEX IF NOT EXISTS idx_risk_logs_account_type ON risk_logs(account_name, risk_type);
CREATE INDEX IF NOT EXISTS idx_risk_logs_unresolved ON risk_logs(resolved) WHERE resolved = FALSE;

-- Backtest run summary.
CREATE TABLE IF NOT EXISTS backtest_runs (
  id BIGSERIAL PRIMARY KEY,
  strategy_name VARCHAR(64) NOT NULL,
  benchmark_symbol VARCHAR(16) NOT NULL DEFAULT '000300',
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  params JSONB,
  annual_return NUMERIC(12, 6),
  max_drawdown NUMERIC(12, 6),
  sharpe_ratio NUMERIC(12, 6),
  win_rate NUMERIC(12, 6),
  total_return NUMERIC(12, 6),
  status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_backtest_runs_status CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
  CONSTRAINT ck_backtest_runs_date_range CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);

-- Backtest daily NAV and drawdown curve.
CREATE TABLE IF NOT EXISTS backtest_nav (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
  trade_date DATE NOT NULL,
  nav NUMERIC(12, 6) NOT NULL,
  drawdown NUMERIC(12, 6) NOT NULL,
  daily_return NUMERIC(12, 6),
  benchmark_nav NUMERIC(12, 6),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_backtest_nav_run_date UNIQUE (run_id, trade_date),
  CONSTRAINT ck_backtest_nav_non_negative CHECK (nav >= 0)
);

CREATE INDEX IF NOT EXISTS idx_backtest_nav_run_date ON backtest_nav(run_id, trade_date);

-- Scheduler execution audit trail.
CREATE TABLE IF NOT EXISTS job_runs (
  id BIGSERIAL PRIMARY KEY,
  job_name VARCHAR(64) NOT NULL,
  run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status VARCHAR(16) NOT NULL,
  message TEXT,
  duration_ms BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_job_runs_status CHECK (status IN ('SUCCESS', 'FAILED', 'SKIPPED'))
);

CREATE INDEX IF NOT EXISTS idx_job_runs_job_name_run_at ON job_runs(job_name, run_at DESC);

COMMIT;
