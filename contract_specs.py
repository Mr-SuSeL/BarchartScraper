"""Contract specifications for the supported Barchart futures markets.

``multiplier`` is the standard exchange contract size in the instrument's
quoted units (for example, 37,500 lb for Coffee and $50 per index point for
the E-mini S&P 500). Exposure calculations use this full contract multiplier.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractSpec:
    ticker: str
    name: str
    multiplier: float
    tick_size: float
    barchart_symbol: str


TICKER_MAPPER = {
    # ICE Coffee C: 37,500 lb; quoted in USD per lb.
    "KC": ContractSpec("KC", "Coffee", 37_500.0, 0.05, "KC*0"),
    # ICE Sugar No. 11: 112,000 lb; quoted in cents per lb.
    "SB": ContractSpec("SB", "Sugar", 112_000.0, 0.01, "SB*0"),
    # ICE Cocoa: 10 metric tons; quoted in USD per metric ton.
    "CC": ContractSpec("CC", "Cocoa", 10.0, 1.0, "CC*0"),
    # NYMEX WTI Crude Oil: 1,000 barrels; quoted in USD per barrel.
    "CL": ContractSpec("CL", "Crude Oil", 1_000.0, 0.01, "CL*0"),
    # CME E-mini S&P 500: $50 per index point.
    "ES": ContractSpec("ES", "E-mini S&P 500", 50.0, 0.25, "ES*0"),
}


def get_contract_spec(ticker: str) -> ContractSpec:
    """Return a supported contract specification, case-insensitively."""
    ticker_clean = ticker.upper().strip()
    try:
        return TICKER_MAPPER[ticker_clean]
    except KeyError as exc:
        available = ", ".join(TICKER_MAPPER)
        raise ValueError(
            f"No contract specification for ticker {ticker_clean!r}. "
            f"Supported tickers: {available}"
        ) from exc
