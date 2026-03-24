import os
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, ValidationError, field_validator, model_validator


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    app_name: str = "Quant Trading Backend"
    app_env: str = "dev"
    app_debug: bool = True
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./quant_trading.db"
    log_level: str = "INFO"
    log_path: str = "logs/app.log"
    cors_origins: list[str] = ["*"]
    default_account: str = "paper_account"
    data_provider: str = "mock"
    tushare_token: str = ""
    strategy_name: str = "multi_factor_v1"
    strategy_top_n: int = 5
    rebalance_weekday: int = 0
    benchmark_symbol: str = "000300.SH"
    timing_ma_window: int = 20
    weight_momentum_20: float = 0.35
    weight_momentum_60: float = 0.25
    weight_volume: float = 0.20
    weight_volatility: float = 0.20
    initial_capital: float = 1_000_000.0
    trade_fee_rate: float = 0.0003
    min_trade_lot: int = 100
    risk_single_position_limit: float = 0.35
    risk_stop_loss_pct: float = -0.08
    risk_max_position_ratio: float = 0.95
    risk_max_drawdown_warning: float = 0.10
    risk_max_drawdown_critical: float = 0.20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Parse CORS origins from string or list format."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            if value.strip() == "*":
                return ["*"]
            return [item.strip() for item in value.split(",") if item.strip()]
        return ["*"]

    @field_validator("data_provider", mode="before")
    @classmethod
    def validate_data_provider(cls, value: Any) -> str:
        """Validate data provider name used by ingestion services."""
        provider = str(value or "mock").strip().lower()
        if provider not in {"mock", "akshare", "tushare"}:
            raise ValueError("DATA_PROVIDER must be one of: mock, akshare, tushare.")
        return provider

    @field_validator("strategy_top_n")
    @classmethod
    def validate_strategy_top_n(cls, value: int) -> int:
        """Validate top-N selection configuration."""
        if value <= 0:
            raise ValueError("STRATEGY_TOP_N must be > 0.")
        return value

    @field_validator("rebalance_weekday")
    @classmethod
    def validate_rebalance_weekday(cls, value: int) -> int:
        """Validate rebalance weekday range (Monday=0 ... Sunday=6)."""
        if value < 0 or value > 6:
            raise ValueError("REBALANCE_WEEKDAY must be between 0 and 6.")
        return value

    @field_validator("timing_ma_window")
    @classmethod
    def validate_timing_ma_window(cls, value: int) -> int:
        """Validate benchmark moving average window."""
        if value <= 1:
            raise ValueError("TIMING_MA_WINDOW must be > 1.")
        return value

    @field_validator("initial_capital")
    @classmethod
    def validate_initial_capital(cls, value: float) -> float:
        """Validate paper trading initial capital."""
        if value <= 0:
            raise ValueError("INITIAL_CAPITAL must be > 0.")
        return value

    @field_validator("trade_fee_rate")
    @classmethod
    def validate_trade_fee_rate(cls, value: float) -> float:
        """Validate transaction fee ratio."""
        if value < 0 or value >= 0.1:
            raise ValueError("TRADE_FEE_RATE must be in [0, 0.1).")
        return value

    @field_validator("min_trade_lot")
    @classmethod
    def validate_min_trade_lot(cls, value: int) -> int:
        """Validate minimum lot size used by paper trading engine."""
        if value <= 0:
            raise ValueError("MIN_TRADE_LOT must be > 0.")
        return value

    @field_validator("risk_single_position_limit")
    @classmethod
    def validate_risk_single_position_limit(cls, value: float) -> float:
        """Validate single-position max weight control."""
        if value <= 0 or value > 1:
            raise ValueError("RISK_SINGLE_POSITION_LIMIT must be in (0, 1].")
        return value

    @field_validator("risk_stop_loss_pct")
    @classmethod
    def validate_risk_stop_loss_pct(cls, value: float) -> float:
        """Validate stop-loss percentage, expected negative ratio."""
        if value >= 0 or value < -0.5:
            raise ValueError("RISK_STOP_LOSS_PCT must be in [-0.5, 0).")
        return value

    @field_validator("risk_max_position_ratio")
    @classmethod
    def validate_risk_max_position_ratio(cls, value: float) -> float:
        """Validate overall exposure max ratio."""
        if value <= 0 or value > 1:
            raise ValueError("RISK_MAX_POSITION_RATIO must be in (0, 1].")
        return value

    @field_validator("risk_max_drawdown_warning")
    @classmethod
    def validate_risk_max_drawdown_warning(cls, value: float) -> float:
        """Validate warning drawdown threshold."""
        if value <= 0 or value >= 1:
            raise ValueError("RISK_MAX_DRAWDOWN_WARNING must be in (0, 1).")
        return value

    @field_validator("risk_max_drawdown_critical")
    @classmethod
    def validate_risk_max_drawdown_critical(cls, value: float) -> float:
        """Validate critical drawdown threshold."""
        if value <= 0 or value >= 1:
            raise ValueError("RISK_MAX_DRAWDOWN_CRITICAL must be in (0, 1).")
        return value

    @model_validator(mode="after")
    def validate_drawdown_threshold_order(self) -> "Settings":
        """Validate drawdown critical threshold must be higher than warning threshold."""
        if self.risk_max_drawdown_critical <= self.risk_max_drawdown_warning:
            raise ValueError("RISK_MAX_DRAWDOWN_CRITICAL must be greater than RISK_MAX_DRAWDOWN_WARNING.")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings object from process environment variables."""
        payload = {
            "app_name": os.getenv("APP_NAME", "Quant Trading Backend"),
            "app_env": os.getenv("APP_ENV", "dev"),
            "app_debug": os.getenv("APP_DEBUG", "true").lower() in {"1", "true", "yes", "on"},
            "api_prefix": os.getenv("API_PREFIX", "/api/v1"),
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", "8000")),
            "database_url": os.getenv("DATABASE_URL", "sqlite:///./quant_trading.db"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_path": os.getenv("LOG_PATH", "logs/app.log"),
            "cors_origins": os.getenv("CORS_ORIGINS", "*"),
            "default_account": os.getenv("DEFAULT_ACCOUNT", "paper_account"),
            "data_provider": os.getenv("DATA_PROVIDER", "mock"),
            "tushare_token": os.getenv("TUSHARE_TOKEN", ""),
            "strategy_name": os.getenv("STRATEGY_NAME", "multi_factor_v1"),
            "strategy_top_n": int(os.getenv("STRATEGY_TOP_N", "5")),
            "rebalance_weekday": int(os.getenv("REBALANCE_WEEKDAY", "0")),
            "benchmark_symbol": os.getenv("BENCHMARK_SYMBOL", "000300.SH").strip().upper(),
            "timing_ma_window": int(os.getenv("TIMING_MA_WINDOW", "20")),
            "weight_momentum_20": float(os.getenv("WEIGHT_MOMENTUM_20", "0.35")),
            "weight_momentum_60": float(os.getenv("WEIGHT_MOMENTUM_60", "0.25")),
            "weight_volume": float(os.getenv("WEIGHT_VOLUME", "0.20")),
            "weight_volatility": float(os.getenv("WEIGHT_VOLATILITY", "0.20")),
            "initial_capital": float(os.getenv("INITIAL_CAPITAL", "1000000")),
            "trade_fee_rate": float(os.getenv("TRADE_FEE_RATE", "0.0003")),
            "min_trade_lot": int(os.getenv("MIN_TRADE_LOT", "100")),
            "risk_single_position_limit": float(os.getenv("RISK_SINGLE_POSITION_LIMIT", "0.35")),
            "risk_stop_loss_pct": float(os.getenv("RISK_STOP_LOSS_PCT", "-0.08")),
            "risk_max_position_ratio": float(os.getenv("RISK_MAX_POSITION_RATIO", "0.95")),
            "risk_max_drawdown_warning": float(os.getenv("RISK_MAX_DRAWDOWN_WARNING", "0.10")),
            "risk_max_drawdown_critical": float(os.getenv("RISK_MAX_DRAWDOWN_CRITICAL", "0.20")),
        }
        return cls(**payload)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache validated settings."""
    try:
        return Settings.from_env()
    except (ValidationError, ValueError) as exc:
        raise RuntimeError("Failed to load application settings.") from exc
