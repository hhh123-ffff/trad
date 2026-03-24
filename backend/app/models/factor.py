from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Factor(Base):
    """Daily factor snapshot table for each stock symbol."""

    __tablename__ = "factors"
    __table_args__ = (UniqueConstraint("stock_id", "trade_date", "factor_version", name="uq_factors_stock_date_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    momentum_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum_60: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    fundamental_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    factor_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
