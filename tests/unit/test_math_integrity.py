import pytest
import numpy as np
from black76 import Black76Engine

def test_vanna_analytical_matches_finite_difference():
    """
    Test merytoryczny: Sprawdza czy analityczna Vanna w Black76 jest równa 
    numerycznej pochodnej Delta względem Implied Volatility (dDelta / dSigma).
    """
    F = 280.0     # Cena futures (np. kawa)
    K = 280.0     # Strike ATM
    T = 0.25      # 3 miesiące do wygaśnięcia
    r = 0.05      # Stopa wolna od ryzyka
    sigma = 0.30  # IV = 30%
    is_call = True

    # 1. Analityczna Vanna z Twojego kodu
    greeks = Black76Engine.calculate_greeks(F, K, T, r, sigma, is_call)
    vanna_analytical = greeks.get('vanna', 0.0)

    # 2. Numeryczna pochodna: d(Delta) / d(sigma)
    h = 1e-5  # Mała zmiana IV
    delta_plus = Black76Engine.calculate_greeks(F, K, T, r, sigma + h, is_call)['delta']
    delta_minus = Black76Engine.calculate_greeks(F, K, T, r, sigma - h, is_call)['delta']
    
    vanna_numerical = (delta_plus - delta_minus) / (2 * h)

    # 3. Weryfikacja merytoryczna: różnica nie może być większa niż 1e-4
    assert vanna_analytical == pytest.approx(vanna_numerical, abs=1e-4), \
        f"Błąd merytoryczny we wzorze Vanna! Analityczna: {vanna_analytical}, Numeryczna: {vanna_numerical}"