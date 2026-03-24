from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logger import logger
from app.models.factor import Factor
from app.models.price import Price
from app.models.stock import Stock
from app.services.strategy.fundamental_provider import FundamentalFactorProvider


@dataclass
class FactorCalculationResult:
    """Summary of one factor calculation run."""

    symbols_processed: int
    trade_dates: int
    records_inserted: int
    records_updated: int


def _safe_zscore(series: pd.Series) -> pd.Series:
    """Compute z-score with zero-variance protection."""
    std = series.std(ddof=0)
    if std is None or std == 0 or np.isnan(std):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - series.mean()) / std


def load_price_panel(
    db: Session,
    symbols: list[str] | None,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Load stock daily close and volume panel from database."""
    stmt = (
        select(Stock.id, Stock.symbol, Price.trade_date, Price.close, Price.volume)
        .join(Price, Price.stock_id == Stock.id)
        .where(and_(Price.trade_date >= start_date, Price.trade_date <= end_date))
        .order_by(Stock.symbol, Price.trade_date)
    )

    if symbols:
        upper_symbols = [item.strip().upper() for item in symbols if item.strip()]
        stmt = stmt.where(Stock.symbol.in_(upper_symbols))

    rows = db.execute(stmt).all()
    if not rows:
        return pd.DataFrame(columns=["stock_id", "symbol", "trade_date", "close", "volume"])

    panel = pd.DataFrame(rows, columns=["stock_id", "symbol", "trade_date", "close", "volume"])
    panel["trade_date"] = pd.to_datetime(panel["trade_date"]).dt.date
    panel["close"] = pd.to_numeric(panel["close"], errors="coerce")
    panel["volume"] = pd.to_numeric(panel["volume"], errors="coerce")
    panel = panel.dropna(subset=["close", "volume"])
    return panel


def compute_factor_dataframe(
    panel: pd.DataFrame,
    fundamental_provider: FundamentalFactorProvider,
) -> pd.DataFrame:
    """Compute momentum, volume, volatility, and total score factors."""
    if panel.empty:
        return pd.DataFrame(
            columns=[
                "stock_id",
                "symbol",
                "trade_date",
                "momentum_20",
                "momentum_60",
                "volume_factor",
                "volatility_20",
                "fundamental_factor",
                "total_score",
                "raw_payload",
            ]
        )

    settings = get_settings()
    panel = panel.sort_values(["symbol", "trade_date"]).copy()

    panel["momentum_20"] = panel.groupby("symbol")["close"].transform(lambda s: s / s.shift(20) - 1)
    panel["momentum_60"] = panel.groupby("symbol")["close"].transform(lambda s: s / s.shift(60) - 1)
    panel["volume_factor"] = panel.groupby("symbol")["volume"].transform(lambda s: s / s.rolling(20).mean() - 1)

    returns = panel.groupby("symbol")["close"].transform(lambda s: s.pct_change())
    panel["volatility_20"] = returns.groupby(panel["symbol"]).transform(lambda s: s.rolling(20).std(ddof=0) * np.sqrt(252))

    factor_dates = sorted(panel["trade_date"].unique().tolist())
    fundamental_map: dict[tuple[str, date], float] = {}
    symbol_list = sorted(panel["symbol"].unique().tolist())
    for factor_date in factor_dates:
        day_map = fundamental_provider.get_factor_map(symbol_list, factor_date)
        for symbol, score in day_map.items():
            fundamental_map[(symbol, factor_date)] = float(score)

    panel["fundamental_factor"] = panel.apply(
        lambda row: fundamental_map.get((row["symbol"], row["trade_date"]), 0.0), axis=1
    )

    panel = panel.dropna(subset=["momentum_20", "momentum_60", "volume_factor", "volatility_20"])
    if panel.empty:
        return pd.DataFrame()

    panel["mom20_z"] = panel.groupby("trade_date")["momentum_20"].transform(_safe_zscore)
    panel["mom60_z"] = panel.groupby("trade_date")["momentum_60"].transform(_safe_zscore)
    panel["volume_z"] = panel.groupby("trade_date")["volume_factor"].transform(_safe_zscore)
    panel["volatility_z"] = -panel.groupby("trade_date")["volatility_20"].transform(_safe_zscore)

    panel["total_score"] = (
        settings.weight_momentum_20 * panel["mom20_z"]
        + settings.weight_momentum_60 * panel["mom60_z"]
        + settings.weight_volume * panel["volume_z"]
        + settings.weight_volatility * panel["volatility_z"]
    )

    panel["raw_payload"] = panel.apply(
        lambda row: {
            "mom20_z": float(row["mom20_z"]),
            "mom60_z": float(row["mom60_z"]),
            "volume_z": float(row["volume_z"]),
            "volatility_z": float(row["volatility_z"]),
        },
        axis=1,
    )

    return panel[
        [
            "stock_id",
            "symbol",
            "trade_date",
            "momentum_20",
            "momentum_60",
            "volume_factor",
            "volatility_20",
            "fundamental_factor",
            "total_score",
            "raw_payload",
        ]
    ]


def upsert_factors(db: Session, factor_df: pd.DataFrame, factor_version: str) -> tuple[int, int]:
    """Insert or update factors table for computed factor DataFrame."""
    if factor_df.empty:
        return (0, 0)

    inserted = 0
    updated = 0

    for row in factor_df.to_dict(orient="records"):
        existing = db.execute(
            select(Factor).where(
                and_(
                    Factor.stock_id == int(row["stock_id"]),
                    Factor.trade_date == row["trade_date"],
                    Factor.factor_version == factor_version,
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                Factor(
                    stock_id=int(row["stock_id"]),
                    trade_date=row["trade_date"],
                    momentum_20=float(row["momentum_20"]),
                    momentum_60=float(row["momentum_60"]),
                    volume_factor=float(row["volume_factor"]),
                    volatility_20=float(row["volatility_20"]),
                    fundamental_factor=float(row["fundamental_factor"]),
                    total_score=float(row["total_score"]),
                    factor_version=factor_version,
                    raw_payload=row["raw_payload"],
                )
            )
            inserted += 1
        else:
            existing.momentum_20 = float(row["momentum_20"])
            existing.momentum_60 = float(row["momentum_60"])
            existing.volume_factor = float(row["volume_factor"])
            existing.volatility_20 = float(row["volatility_20"])
            existing.fundamental_factor = float(row["fundamental_factor"])
            existing.total_score = float(row["total_score"])
            existing.raw_payload = row["raw_payload"]
            updated += 1

    return (inserted, updated)


class FactorEngine:
    """Factor engine for multi-factor daily calculations."""

    def __init__(self, fundamental_provider: FundamentalFactorProvider | None = None) -> None:
        """Initialize factor engine with optional fundamental provider."""
        self.fundamental_provider = fundamental_provider or FundamentalFactorProvider()

    def run(
        self,
        db: Session,
        start_date: date,
        end_date: date,
        symbols: list[str] | None = None,
        factor_version: str = "v1",
    ) -> FactorCalculationResult:
        """Run factor calculation and persistence for selected symbols and dates."""
        try:
            panel = load_price_panel(db=db, symbols=symbols, start_date=start_date, end_date=end_date)
            factor_df = compute_factor_dataframe(panel=panel, fundamental_provider=self.fundamental_provider)
            inserted, updated = upsert_factors(db=db, factor_df=factor_df, factor_version=factor_version)
            db.commit()

            trade_dates = 0 if factor_df.empty else factor_df["trade_date"].nunique()
            symbols_processed = 0 if factor_df.empty else factor_df["symbol"].nunique()

            result = FactorCalculationResult(
                symbols_processed=int(symbols_processed),
                trade_dates=int(trade_dates),
                records_inserted=inserted,
                records_updated=updated,
            )
            logger.info("Factor engine completed: {}", result)
            return result
        except Exception as exc:
            db.rollback()
            logger.exception("Factor engine execution failed: {}", exc)
            raise
