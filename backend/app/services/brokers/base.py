from abc import ABC, abstractmethod


class BrokerAdapter(ABC):
    """Abstract broker adapter interface reserved for future live trading."""

    @abstractmethod
    def get_account(self) -> dict:
        """Return account summary information from broker."""

    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: int, price: float) -> dict:
        """Submit an order to broker and return broker response."""

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> dict:
        """Cancel an existing order from broker."""

    @abstractmethod
    def get_positions(self) -> list[dict]:
        """Return current broker positions list."""
