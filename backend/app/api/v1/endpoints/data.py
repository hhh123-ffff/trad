from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.data import DataSyncRequest, DataSyncResponse
from app.services.data.ingestion import MarketDataIngestionService

router = APIRouter()


@router.post("/data/sync", response_model=DataSyncResponse)
def sync_data(payload: DataSyncRequest, db: Session = Depends(get_db)) -> DataSyncResponse:
    """Run manual data synchronization and return execution summary."""
    service = MarketDataIngestionService()
    result = service.run_full_sync(
        db=db,
        symbols=payload.symbols,
        start_date=payload.start_date,
        end_date=payload.end_date,
        include_stock_universe=payload.include_stock_universe,
    )

    return DataSyncResponse(
        provider=result.provider,
        stock_count=result.stock_count,
        price_inserted=result.price_inserted,
        price_updated=result.price_updated,
        symbols_processed=result.symbols_processed,
    )
