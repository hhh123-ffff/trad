from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.simulation import SimulationRunRequest, SimulationRunResponse
from app.services.simulation.engine import PaperTradingEngine

router = APIRouter()


@router.post("/simulation/run", response_model=SimulationRunResponse)
def run_simulation(payload: SimulationRunRequest, db: Session = Depends(get_db)) -> SimulationRunResponse:
    """Run paper trading simulation based on generated signals."""
    engine = PaperTradingEngine()
    result = engine.run(
        db=db,
        run_date=payload.trade_date,
        account_name=payload.account_name,
    )

    return SimulationRunResponse(
        account_name=result.account_name,
        trade_date=result.trade_date,
        signal_count=result.signal_count,
        orders_created=result.orders_created,
        buy_count=result.buy_count,
        sell_count=result.sell_count,
        rejected_count=result.rejected_count,
        holding_count=result.holding_count,
        cash=result.cash,
        market_value=result.market_value,
        total_asset=result.total_asset,
        position_ratio=result.position_ratio,
    )
