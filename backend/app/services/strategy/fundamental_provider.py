from datetime import date


class FundamentalFactorProvider:
    """Placeholder provider for fundamental factor integration."""

    def get_factor_map(self, symbols: list[str], trade_date: date) -> dict[str, float]:
        """Return symbol to fundamental factor score map for one trade date."""
        return {symbol: 0.0 for symbol in symbols}
