import math

import pytest
from scipy.stats import norm

from black76 import Black76Engine


@pytest.mark.parametrize(
    'kwargs',
    [
        {'F': 100.0, 'K': 100.0, 'T': 0.0, 'r': 0.05, 'sigma': 0.20, 'is_call': True},
        {'F': 100.0, 'K': 100.0, 'T': 1.0, 'r': 0.05, 'sigma': 0.0, 'is_call': True},
        {'F': 0.0, 'K': 100.0, 'T': 1.0, 'r': 0.05, 'sigma': 0.20, 'is_call': True},
        {'F': 100.0, 'K': 0.0, 'T': 1.0, 'r': 0.05, 'sigma': 0.20, 'is_call': False},
    ],
)
def test_calculate_greeks_returns_zero_for_invalid_inputs(kwargs):
    print("[INFO] Sprawdzanie zerowych greków dla danych brzegowych...")
    expected = {
        'delta': 0.0,
        'gamma': 0.0,
        'vega': 0.0,
        'vanna': 0.0,
        'charm': 0.0,
        'vomma': 0.0,
    }
    assert Black76Engine.calculate_greeks(**kwargs) == expected


def test_calculate_greeks_for_atm_call_matches_expected_values():
    print("[INFO] Obliczanie greków dla opcji ATM i porównanie z wartościami wzorcowymi...")
    greeks = Black76Engine.calculate_greeks(100.0, 100.0, 1.0, 0.05, 0.20, True)

    assert greeks['delta'] == pytest.approx(0.5135001229824934, rel=1e-7)
    assert greeks['gamma'] == pytest.approx(0.018879647164532515, rel=1e-7)
    assert greeks['vega'] == pytest.approx(0.3775929432906503, rel=1e-7)
    assert greeks['vanna'] == pytest.approx(0.18879647164532512, rel=1e-7)
    assert greeks['charm'] == pytest.approx(
        Black76Engine.calculate_charm(100.0, 100.0, 1.0, 0.05, 0.20, True),
        rel=1e-7,
    )
    assert greeks['vomma'] == pytest.approx(-0.01887964716453252, rel=1e-7)


def test_charm_differs_between_call_and_put():
    print("[INFO] Weryfikacja odrębnych wzorów Charm dla Call i Put...")
    call_charm = Black76Engine.calculate_charm(100.0, 100.0, 1.0, 0.05, 0.20, True)
    put_charm = Black76Engine.calculate_charm(100.0, 100.0, 1.0, 0.05, 0.20, False)

    assert call_charm != pytest.approx(put_charm)
    assert call_charm - put_charm == pytest.approx(
        math.exp(-0.05) * 0.05 / 365.0,
        rel=1e-7,
    )


def test_implied_volatility_inverts_option_price():
    print("[INFO] Wyznaczanie ceny opcji dla znanej zmienności...")
    spot = 100.0
    strike = 100.0
    time_to_expiry = 1.0
    rate = 0.05
    sigma = 0.22

    sqrt_t = math.sqrt(time_to_expiry)
    d1 = (math.log(spot / strike) + 0.5 * sigma ** 2 * time_to_expiry) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    price = math.exp(-rate * time_to_expiry) * (spot * norm.cdf(d1) - strike * norm.cdf(d2))

    print("[INFO] Odwracanie ceny w celu odzyskania zmienności implikowanej...")
    implied = Black76Engine.implied_volatility(price, spot, strike, time_to_expiry, rate, True)

    assert implied == pytest.approx(sigma, abs=1e-6)


def test_implied_volatility_returns_zero_for_invalid_pricing_data():
    print("[INFO] Weryfikacja zmienności implikowanej dla nieprawidłowych danych...")
    assert Black76Engine.implied_volatility(0.0, 100.0, 100.0, 1.0, 0.05, True) == 0.0
    assert Black76Engine.implied_volatility(5.0, 100.0, 100.0, 0.0, 0.05, True) == 0.0
