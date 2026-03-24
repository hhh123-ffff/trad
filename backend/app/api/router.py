from fastapi import APIRouter

from app.api.v1.endpoints import backtest, dashboard, data, health, orders, positions, risk, signals, simulation, strategy

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(positions.router, tags=["positions"])
api_router.include_router(orders.router, tags=["orders"])
api_router.include_router(signals.router, tags=["signals"])
api_router.include_router(backtest.router, tags=["backtest"])
api_router.include_router(risk.router, tags=["risk"])
api_router.include_router(data.router, tags=["data"])
api_router.include_router(strategy.router, tags=["strategy"])
api_router.include_router(simulation.router, tags=["simulation"])
