/** Shared response type for dashboard NAV point. */
export interface NavPoint {
  trade_date: string;
  nav: number;
}

/** Dashboard aggregate metrics returned by backend. */
export interface DashboardOverview {
  total_asset: number;
  cash: number;
  market_value: number;
  today_pnl: number;
  cumulative_return: number;
  position_ratio: number;
  max_drawdown: number;
  nav_series: NavPoint[];
  stock_universe_size: number;
}

/** Position item used by positions page table. */
export interface PositionView {
  snapshot_date: string;
  symbol: string;
  name: string;
  quantity: number;
  avg_cost: number;
  last_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  weight: number;
  stop_loss_price: number | null;
}

/** Order item used by orders page table. */
export interface OrderView {
  order_id: number;
  account_name: string;
  order_date: string;
  symbol: string;
  side: string;
  quantity: number;
  filled_quantity: number;
  price: number;
  fee: number;
  status: string;
  note: string;
}

/** Signal item used by strategy signal page table. */
export interface SignalView {
  trade_date: string;
  symbol: string;
  strategy_name: string;
  action: string;
  score: number;
  target_weight: number;
  reason: string;
  status: string;
  momentum_20: number | null;
  momentum_60: number | null;
  volume_factor: number | null;
  volatility_20: number | null;
  fundamental_factor: number | null;
}

/** One point on backtest curve. */
export interface CurvePoint {
  trade_date: string;
  nav: number;
  drawdown: number;
  daily_return: number;
  benchmark_nav: number | null;
}

/** Latest backtest overview payload. */
export interface BacktestOverview {
  run_id: number | null;
  strategy_name: string;
  benchmark_symbol: string;
  start_date: string | null;
  end_date: string | null;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_return: number;
  status: string;
  curve: CurvePoint[];
}

/** Compact backtest run row used by history list endpoint. */
export interface BacktestRunItem {
  run_id: number;
  strategy_name: string;
  benchmark_symbol: string;
  start_date: string;
  end_date: string;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_return: number;
  status: string;
  created_at: string;
}

/** Paginated backtest run list response. */
export interface BacktestRunListResponse {
  total: number;
  limit: number;
  offset: number;
  items: BacktestRunItem[];
}

/** Risk alert item for risk panel. */
export interface RiskAlert {
  level: "INFO" | "WARNING" | "CRITICAL" | string;
  risk_type: string;
  message: string;
}

/** Risk status response payload. */
export interface RiskStatus {
  overall_level: "INFO" | "WARNING" | "CRITICAL" | string;
  max_drawdown: number;
  position_ratio: number;
  alerts: RiskAlert[];
}
