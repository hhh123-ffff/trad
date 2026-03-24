from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logger import logger
from app.models.backtest_nav import BacktestNav
from app.models.backtest_run import BacktestRun
from app.models.factor import Factor
from app.models.price import Price
from app.models.stock import Stock
from app.schemas.backtest import BacktestOverview, BacktestRunItem, BacktestRunListResponse, CurvePoint
from app.services.strategy.factor_engine import FactorEngine


@dataclass
class BacktestContext:
    """Runtime context used by backtest simulation loop."""

    trade_dates: list[date]
    returns_df: pd.DataFrame
    factor_map: dict[date, list[tuple[int, float]]]
    timing_map: dict[date, tuple[bool, str]]
    benchmark_nav_map: dict[date, float]


@dataclass
class BacktestComputationResult:
    """Raw computation result before persistence."""

    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_return: float
    curve: list[CurvePoint]


@dataclass
class BacktestRunConfig:
    """Backtest execution configuration."""

    start_date: date
    end_date: date
    top_n: int
    strategy_name: str
    factor_version: str
    initial_nav: float
    force_rebalance: bool


class BacktestEngine:
    """Historical backtest engine for multi-factor weekly rebalance strategy."""

    def __init__(self, factor_engine: FactorEngine | None = None) -> None:
        """Initialize backtest engine with optional factor engine dependency."""
        self.factor_engine = factor_engine or FactorEngine()

    @staticmethod
    def _load_price_panel(db: Session, start_date: date, end_date: date) -> pd.DataFrame:
        """Load daily close price panel for all stocks in date range."""
        rows = db.execute(
            select(Price.trade_date, Price.stock_id, Price.close)
            .where(and_(Price.trade_date >= start_date, Price.trade_date <= end_date))
            .order_by(Price.trade_date, Price.stock_id)
        ).all()

        if not rows:
            return pd.DataFrame(columns=["trade_date", "stock_id", "close"])

        panel = pd.DataFrame(rows, columns=["trade_date", "stock_id", "close"])
        panel["trade_date"] = pd.to_datetime(panel["trade_date"]).dt.date
        panel["close"] = pd.to_numeric(panel["close"], errors="coerce")
        panel = panel.dropna(subset=["close"])
        return panel

    @staticmethod
    def _load_factor_map(db: Session, start_date: date, end_date: date, factor_version: str) -> dict[date, list[tuple[int, float]]]:
        """Load factor ranking map keyed by trade date."""
        rows = db.execute(
            select(Factor.trade_date, Factor.stock_id, Factor.total_score)
            .where(
                and_(
                    Factor.trade_date >= start_date,
                    Factor.trade_date <= end_date,
                    Factor.factor_version == factor_version,
                    Factor.total_score.is_not(None),
                )
            )
            .order_by(Factor.trade_date, Factor.total_score.desc())
        ).all()

        factor_map: dict[date, list[tuple[int, float]]] = {}
        for trade_date, stock_id, score in rows:
            factor_map.setdefault(trade_date, []).append((int(stock_id), float(score)))
        return factor_map

    @staticmethod
    def _prepare_benchmark_context(
        db: Session,
        start_date: date,
        end_date: date,
        benchmark_symbol: str,
        ma_window: int,
        initial_nav: float,
    ) -> tuple[dict[date, tuple[bool, str]], dict[date, float]]:
        """Build benchmark timing and benchmark NAV maps for backtest period."""
        benchmark_id = db.scalar(select(Stock.id).where(Stock.symbol == benchmark_symbol))
        if benchmark_id is None:
            return (
                {},
                {},
            )

        lookback_start = start_date - timedelta(days=ma_window * 4)
        rows = db.execute(
            select(Price.trade_date, Price.close)
            .where(
                and_(
                    Price.stock_id == benchmark_id,
                    Price.trade_date >= lookback_start,
                    Price.trade_date <= end_date,
                )
            )
            .order_by(Price.trade_date)
        ).all()

        if not rows:
            return ({}, {})

        benchmark_df = pd.DataFrame(rows, columns=["trade_date", "close"])
        benchmark_df["trade_date"] = pd.to_datetime(benchmark_df["trade_date"]).dt.date
        benchmark_df["close"] = pd.to_numeric(benchmark_df["close"], errors="coerce")
        benchmark_df = benchmark_df.dropna(subset=["close"])
        if benchmark_df.empty:
            return ({}, {})

        benchmark_df["ma"] = benchmark_df["close"].rolling(ma_window).mean()
        benchmark_df["ret"] = benchmark_df["close"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)

        benchmark_nav_map: dict[date, float] = {}
        nav = float(initial_nav)
        for row in benchmark_df.itertuples(index=False):
            if row.trade_date < start_date:
                continue
            nav *= 1.0 + float(row.ret)
            benchmark_nav_map[row.trade_date] = nav

        timing_map: dict[date, tuple[bool, str]] = {}
        for row in benchmark_df.itertuples(index=False):
            if row.trade_date < start_date:
                continue
            if pd.isna(row.ma):
                timing_map[row.trade_date] = (True, "Benchmark MA unavailable. Timing filter skipped.")
                continue
            if float(row.close) >= float(row.ma):
                timing_map[row.trade_date] = (
                    True,
                    f"Timing passed: benchmark close {float(row.close):.4f} >= MA{ma_window} {float(row.ma):.4f}.",
                )
            else:
                timing_map[row.trade_date] = (
                    False,
                    f"Timing blocked: benchmark close {float(row.close):.4f} < MA{ma_window} {float(row.ma):.4f}.",
                )

        return (timing_map, benchmark_nav_map)

    def _build_context(self, db: Session, config: BacktestRunConfig) -> BacktestContext:
        """Build backtest simulation context from persisted data."""
        settings = get_settings()

        panel = self._load_price_panel(db=db, start_date=config.start_date, end_date=config.end_date)
        if panel.empty:
            return BacktestContext(
                trade_dates=[],
                returns_df=pd.DataFrame(),
                factor_map={},
                timing_map={},
                benchmark_nav_map={},
            )

        price_pivot = panel.pivot(index="trade_date", columns="stock_id", values="close").sort_index()
        returns_df = price_pivot.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
        trade_dates = [pd.to_datetime(item).date() for item in returns_df.index.tolist()]

        factor_map = self._load_factor_map(
            db=db,
            start_date=config.start_date,
            end_date=config.end_date,
            factor_version=config.factor_version,
        )

        timing_map, benchmark_nav_map = self._prepare_benchmark_context(
            db=db,
            start_date=config.start_date,
            end_date=config.end_date,
            benchmark_symbol=settings.benchmark_symbol,
            ma_window=settings.timing_ma_window,
            initial_nav=config.initial_nav,
        )

        return BacktestContext(
            trade_dates=trade_dates,
            returns_df=returns_df,
            factor_map=factor_map,
            timing_map=timing_map,
            benchmark_nav_map=benchmark_nav_map,
        )

    @staticmethod
    def _compute_metrics(curve: list[CurvePoint], initial_nav: float) -> tuple[float, float, float, float, float]:
        """Compute annual return, drawdown, sharpe, win rate, and total return."""
        if not curve:
            return (0.0, 0.0, 0.0, 0.0, 0.0)

        daily_returns = [point.daily_return for point in curve[1:]]
        nav_end = float(curve[-1].nav)
        total_return = nav_end / initial_nav - 1.0

        if daily_returns:
            mean_ret = float(np.mean(daily_returns))
            std_ret = float(np.std(daily_returns))
            sharpe = 0.0 if std_ret == 0 else mean_ret / std_ret * np.sqrt(252)
            win_rate = float(sum(1 for item in daily_returns if item > 0) / len(daily_returns))
            annual_return = float((nav_end / initial_nav) ** (252 / len(daily_returns)) - 1.0)
        else:
            sharpe = 0.0
            win_rate = 0.0
            annual_return = 0.0

        max_drawdown = abs(min(point.drawdown for point in curve))
        return (annual_return, max_drawdown, sharpe, win_rate, total_return)

    def _simulate(self, config: BacktestRunConfig, context: BacktestContext) -> BacktestComputationResult:
        """Simulate historical portfolio NAV using weekly factor rebalancing."""
        settings = get_settings()
        if not context.trade_dates:
            return BacktestComputationResult(
                annual_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                total_return=0.0,
                curve=[],
            )

        nav = float(config.initial_nav)
        peak = nav
        weights: dict[int, float] = {}
        pending_weights: dict[int, float] | None = None
        curve: list[CurvePoint] = []
        last_benchmark_nav = config.initial_nav

        for index, trade_day in enumerate(context.trade_dates):
            if pending_weights is not None:
                weights = pending_weights
                pending_weights = None

            daily_return = 0.0
            if index > 0 and weights:
                row = context.returns_df.loc[trade_day]
                for stock_id, weight in weights.items():
                    value = row.get(stock_id, 0.0)
                    if pd.isna(value):
                        value = 0.0
                    daily_return += float(weight) * float(value)

            nav *= 1.0 + daily_return
            peak = max(peak, nav)
            drawdown = nav / peak - 1.0 if peak > 0 else 0.0

            if trade_day in context.benchmark_nav_map:
                last_benchmark_nav = context.benchmark_nav_map[trade_day]

            curve.append(
                CurvePoint(
                    trade_date=trade_day,
                    nav=round(float(nav), 6),
                    drawdown=round(float(drawdown), 6),
                    daily_return=round(float(daily_return), 6),
                    benchmark_nav=round(float(last_benchmark_nav), 6) if context.benchmark_nav_map else None,
                )
            )

            rebalance_day = config.force_rebalance or trade_day.weekday() == settings.rebalance_weekday
            if not rebalance_day:
                continue

            timing_passed, _ = context.timing_map.get(
                trade_day,
                (True, "Benchmark data not found. Timing filter skipped."),
            )
            if not timing_passed:
                pending_weights = {}
                continue

            ranked = context.factor_map.get(trade_day, [])
            selected = [stock_id for stock_id, _ in ranked[: config.top_n] if stock_id in context.returns_df.columns]
            if not selected:
                pending_weights = {}
                continue

            equal_weight = 1.0 / len(selected)
            pending_weights = {stock_id: equal_weight for stock_id in selected}

        annual_return, max_drawdown, sharpe, win_rate, total_return = self._compute_metrics(
            curve=curve,
            initial_nav=config.initial_nav,
        )

        return BacktestComputationResult(
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            total_return=total_return,
            curve=curve,
        )

    @staticmethod
    def _persist_result(db: Session, config: BacktestRunConfig, result: BacktestComputationResult) -> int:
        """Persist backtest summary and NAV curve; return generated run id."""
        settings = get_settings()
        run = BacktestRun(
            strategy_name=config.strategy_name,
            benchmark_symbol=settings.benchmark_symbol,
            start_date=config.start_date,
            end_date=config.end_date,
            params={
                "top_n": config.top_n,
                "factor_version": config.factor_version,
                "initial_nav": config.initial_nav,
                "force_rebalance": config.force_rebalance,
            },
            annual_return=float(result.annual_return),
            max_drawdown=float(result.max_drawdown),
            sharpe_ratio=float(result.sharpe_ratio),
            win_rate=float(result.win_rate),
            total_return=float(result.total_return),
            status="SUCCESS",
        )
        db.add(run)
        db.flush()

        for point in result.curve:
            db.add(
                BacktestNav(
                    run_id=run.id,
                    trade_date=point.trade_date,
                    nav=float(point.nav),
                    drawdown=float(point.drawdown),
                    daily_return=float(point.daily_return),
                    benchmark_nav=None if point.benchmark_nav is None else float(point.benchmark_nav),
                )
            )

        return int(run.id)

    def run(
        self,
        db: Session,
        start_date: date,
        end_date: date,
        top_n: int | None = None,
        strategy_name: str | None = None,
        factor_version: str = "v1",
        initial_nav: float = 1.0,
        force_rebalance: bool = False,
    ) -> BacktestOverview:
        """Execute one historical backtest run and return persisted overview."""
        settings = get_settings()
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date.")

        final_top_n = top_n or settings.strategy_top_n
        final_strategy_name = strategy_name or settings.strategy_name

        try:
            factor_start = start_date - timedelta(days=100)
            self.factor_engine.run(
                db=db,
                start_date=factor_start,
                end_date=end_date,
                symbols=None,
                factor_version=factor_version,
            )

            config = BacktestRunConfig(
                start_date=start_date,
                end_date=end_date,
                top_n=final_top_n,
                strategy_name=final_strategy_name,
                factor_version=factor_version,
                initial_nav=initial_nav,
                force_rebalance=force_rebalance,
            )
            context = self._build_context(db=db, config=config)
            result = self._simulate(config=config, context=context)
            run_id = self._persist_result(db=db, config=config, result=result)
            db.commit()

            overview = BacktestOverview(
                run_id=run_id,
                strategy_name=final_strategy_name,
                benchmark_symbol=settings.benchmark_symbol,
                start_date=start_date,
                end_date=end_date,
                annual_return=float(result.annual_return),
                max_drawdown=float(result.max_drawdown),
                sharpe_ratio=float(result.sharpe_ratio),
                win_rate=float(result.win_rate),
                total_return=float(result.total_return),
                status="SUCCESS",
                curve=result.curve,
            )
            logger.info("Backtest engine completed: run_id={} annual_return={} max_drawdown={}", run_id, result.annual_return, result.max_drawdown)
            return overview
        except Exception as exc:
            db.rollback()
            logger.exception("Backtest engine execution failed: {}", exc)
            raise


def get_backtest_overview(db: Session, run_id: int | None = None) -> BacktestOverview:
    """Load latest or selected backtest run overview from database."""
    run_stmt = select(BacktestRun)
    if run_id is not None:
        run_stmt = run_stmt.where(BacktestRun.id == run_id)
    else:
        run_stmt = run_stmt.order_by(BacktestRun.created_at.desc()).limit(1)

    run = db.execute(run_stmt).scalar_one_or_none()
    if run is None:
        return BacktestOverview(
            annual_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            total_return=0.0,
            status="EMPTY",
            curve=[],
        )

    curve_rows = db.execute(
        select(BacktestNav)
        .where(BacktestNav.run_id == run.id)
        .order_by(BacktestNav.trade_date)
    ).scalars().all()

    curve = [
        CurvePoint(
            trade_date=row.trade_date,
            nav=float(row.nav),
            drawdown=float(row.drawdown),
            daily_return=float(row.daily_return),
            benchmark_nav=(None if row.benchmark_nav is None else float(row.benchmark_nav)),
        )
        for row in curve_rows
    ]

    return BacktestOverview(
        run_id=int(run.id),
        strategy_name=run.strategy_name,
        benchmark_symbol=run.benchmark_symbol,
        start_date=run.start_date,
        end_date=run.end_date,
        annual_return=float(run.annual_return),
        max_drawdown=float(run.max_drawdown),
        sharpe_ratio=float(run.sharpe_ratio),
        win_rate=float(run.win_rate),
        total_return=float(run.total_return),
        status=run.status,
        curve=curve,
    )


def list_backtest_runs(
    db: Session,
    limit: int = 20,
    offset: int = 0,
    strategy_name: str | None = None,
) -> BacktestRunListResponse:
    """List persisted backtest run summaries with pagination and optional strategy filter."""
    stmt = select(BacktestRun)
    count_stmt = select(func.count(BacktestRun.id))

    if strategy_name:
        stmt = stmt.where(BacktestRun.strategy_name == strategy_name)
        count_stmt = count_stmt.where(BacktestRun.strategy_name == strategy_name)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.execute(
        stmt.order_by(BacktestRun.created_at.desc()).offset(offset).limit(limit)
    ).scalars().all()

    items = [
        BacktestRunItem(
            run_id=int(row.id),
            strategy_name=row.strategy_name,
            benchmark_symbol=row.benchmark_symbol,
            start_date=row.start_date,
            end_date=row.end_date,
            annual_return=float(row.annual_return),
            max_drawdown=float(row.max_drawdown),
            sharpe_ratio=float(row.sharpe_ratio),
            win_rate=float(row.win_rate),
            total_return=float(row.total_return),
            status=row.status,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return BacktestRunListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
