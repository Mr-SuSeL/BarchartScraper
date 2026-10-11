import pandas as pd
import pytest

from black76 import Black76Engine
from contract_specs import TICKER_MAPPER, get_contract_spec
from exposure_engine import OptionExposureCalculator


@pytest.mark.parametrize("ticker,spec", TICKER_MAPPER.items())
def test_exposure_uses_market_contract_multiplier(ticker, spec, tmp_path):
    spot = 100.0
    strike = 100.0
    expiry = 0.25
    rate = 0.03
    volatility = 0.2
    open_interest = 20.0
    calculator = OptionExposureCalculator(
        spot_price=spot,
        risk_free_rate=rate,
        cache_dir=str(tmp_path / ticker),
    )
    options = pd.DataFrame(
        [
            {
                "strike": strike,
                "option_type": "CALL",
                "open_interest": open_interest,
                "mid_price": 5.0,
                "iv": volatility,
            }
        ]
    )

    result = calculator.compute_exposures(options, expiry, ticker=ticker)
    greeks = Black76Engine.calculate_greeks(
        spot, strike, expiry, rate, volatility, is_call=True
    )

    assert calculator.multiplier == spec.multiplier
    assert result.loc[0, "gex"] == pytest.approx(
        greeks["gamma"] * open_interest * spec.multiplier * 0.01 * spot**2
    )
    assert result.loc[0, "vex"] == pytest.approx(
        greeks["vanna"] * open_interest * spec.multiplier * spot * 0.01
    )


def test_default_market_is_kc_and_ticker_lookup_is_case_insensitive(tmp_path):
    calculator = OptionExposureCalculator(spot_price=100.0, cache_dir=str(tmp_path))

    assert calculator.multiplier == get_contract_spec("KC").multiplier
    assert get_contract_spec(" es ") == TICKER_MAPPER["ES"]

    options = pd.DataFrame(
        [
            {
                "strike": 100.0,
                "option_type": "CALL",
                "open_interest": 1.0,
                "mid_price": 5.0,
                "iv": 0.2,
            }
        ]
    )
    calculator.compute_exposures(options, time_to_expiry_years=0.25)

    assert calculator.multiplier == TICKER_MAPPER["KC"].multiplier


def test_unknown_ticker_raises_clear_error(tmp_path):
    calculator = OptionExposureCalculator(spot_price=100.0, cache_dir=str(tmp_path))
    options = pd.DataFrame(
        [
            {
                "strike": 100.0,
                "option_type": "CALL",
                "open_interest": 1.0,
                "mid_price": 5.0,
                "iv": 0.2,
            }
        ]
    )

    with pytest.raises(ValueError, match="No contract specification.*'UNKNOWN'"):
        calculator.compute_exposures(options, time_to_expiry_years=0.25, ticker="unknown")


def test_explicit_legacy_multiplier_remains_an_override(tmp_path):
    calculator = OptionExposureCalculator(
        spot_price=100.0,
        multiplier=123.0,
        cache_dir=str(tmp_path),
    )
    options = pd.DataFrame(
        [
            {
                "strike": 100.0,
                "option_type": "CALL",
                "open_interest": 1.0,
                "mid_price": 5.0,
                "iv": 0.2,
            }
        ]
    )

    result = calculator.compute_exposures(options, 0.25, ticker="ES")
    greeks = Black76Engine.calculate_greeks(100.0, 100.0, 0.25, 0.045, 0.2, True)

    assert calculator.multiplier == 123.0
    assert result.loc[0, "gex"] == pytest.approx(
        greeks["gamma"] * 123.0 * 0.01 * 100.0**2
    )
