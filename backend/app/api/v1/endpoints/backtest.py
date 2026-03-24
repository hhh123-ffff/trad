from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.backtest import BacktestOverview, BacktestRunListResponse, BacktestRunRequest, BacktestRunResponse
from app.services.backtest.engine import BacktestEngine, list_backtest_runs
from app.services.trading_service import get_backtest_overview

router = APIRouter()


@router.get("/backtest", response_model=BacktestOverview)
def get_backtest(
    run_id: int | None = Query(default=None, ge=1, description="Specific backtest run id."),
    db: Session = Depends(get_db),
) -> BacktestOverview:
    """Return latest or selected backtest metrics and curve data."""
    return get_backtest_overview(db=db, run_id=run_id)


@router.get("/backtest/runs", response_model=BacktestRunListResponse)
def get_backtest_runs(
    strategy_name: str | None = Query(default=None, description="Filter by strategy name."),
    limit: int = Query(default=20, ge=1, le=200, description="Maximum number of items."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    db: Session = Depends(get_db),
) -> BacktestRunListResponse:
    """Return paginated historical backtest run summaries."""
    return list_backtest_runs(
        db=db,
        limit=limit,
        offset=offset,
        strategy_name=strategy_name,
    )


@router.post("/backtest/run", response_model=BacktestRunResponse)
def run_backtest(payload: BacktestRunRequest, db: Session = Depends(get_db)) -> BacktestRunResponse:
    """Run historical backtest and persist run summary with NAV curve."""
    engine = BacktestEngine()
    overview = engine.run(
        db=db,
        start_date=payload.start_date,
        end_date=payload.end_date,
        top_n=payload.top_n,
        strategy_name=payload.strategy_name,
        factor_version=payload.factor_version,
        initial_nav=payload.initial_nav,
        force_rebalance=payload.force_rebalance,
    )
    return BacktestRunResponse(**overview.model_dump())
