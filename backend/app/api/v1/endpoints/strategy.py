from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.strategy import FactorRunRequest, FactorRunResponse, StrategyRunRequest, StrategyRunResponse
from app.services.strategy.factor_engine import FactorEngine
from app.services.strategy.strategy_engine import MultiFactorStrategyEngine

router = APIRouter()


@router.post("/factors/calculate", response_model=FactorRunResponse)
def calculate_factors(payload: FactorRunRequest, db: Session = Depends(get_db)) -> FactorRunResponse:
    """Run factor engine for selected date range and symbols."""
    engine = FactorEngine()
    result = engine.run(
        db=db,
        start_date=payload.start_date,
        end_date=payload.end_date,
        symbols=payload.symbols,
        factor_version=payload.factor_version,
    )
    return FactorRunResponse(
        symbols_processed=result.symbols_processed,
        trade_dates=result.trade_dates,
        records_inserted=result.records_inserted,
        records_updated=result.records_updated,
    )


@router.post("/strategy/run", response_model=StrategyRunResponse)
def run_strategy(payload: StrategyRunRequest, db: Session = Depends(get_db)) -> StrategyRunResponse:
    """Run multi-factor strategy and persist latest rebalance signals."""
    engine = MultiFactorStrategyEngine()
    result = engine.run(
        db=db,
        trade_date=payload.trade_date,
        top_n=payload.top_n,
        strategy_name=payload.strategy_name,
        factor_version=payload.factor_version,
        force_rebalance=payload.force_rebalance,
    )
    return StrategyRunResponse(
        trade_date=result.trade_date,
        strategy_name=result.strategy_name,
        status=result.status,
        timing_passed=result.timing_passed,
        reason=result.reason,
        selected_count=result.selected_count,
        buy_count=result.buy_count,
        sell_count=result.sell_count,
        hold_count=result.hold_count,
    )
