import math
from scipy.stats import norm

class Black76Engine:
    """Silnik matematyczny Blacka-76 do wyceny i obliczania greków opcji na futures."""

    @staticmethod
    def calculate_charm(F: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
        if T <= 0.00001 or sigma <= 0.001 or F <= 0 or K <= 0:
            return 0.0

        df = math.exp(-r * T)
        sqrt_t = math.sqrt(T)
        d1 = (math.log(F / K) + 0.5 * (sigma**2) * T) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t
        pdf_d1 = norm.pdf(d1)

        if is_call:
            charm_annual = df * (r * norm.cdf(d1) + (pdf_d1 * d2) / (2.0 * T))
        else:
            charm_annual = df * (-r * norm.cdf(-d1) + (pdf_d1 * d2) / (2.0 * T))

        return float(charm_annual / 365.0)

    @staticmethod
    def calculate_greeks(F: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> dict:
        empty_greeks = {
            "delta": 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "vanna": 0.0,
            "charm": 0.0,
            "vomma": 0.0,
        }

        if T <= 0.00001 or sigma <= 0.001 or F <= 0 or K <= 0:
            return empty_greeks

        df = math.exp(-r * T)
        sqrt_t = math.sqrt(T)

        d1 = (math.log(F / K) + 0.5 * (sigma**2) * T) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t

        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)

        if is_call:
            delta = df * cdf_d1
        else:
            delta = -df * norm.cdf(-d1)

        gamma = (df * pdf_d1) / (F * sigma * sqrt_t)
        vega = (F * df * pdf_d1 * sqrt_t) / 100.0
        vanna = -df * pdf_d1 * (d2 / sigma)
        charm = Black76Engine.calculate_charm(F, K, T, r, sigma, is_call)
        
        # Volga/Vomma - z racji, że 'vega' wyżej jest podzielona przez 100, 
        # vomma również prawidłowo reprezentuje zmianę co 1% IV.
        vomma = vega * (d1 * d2 / sigma)

        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "vanna": float(vanna),
            "charm": float(charm),
            "vomma": float(vomma),
        }

    @classmethod
    def implied_volatility(
        cls, price: float, F: float, K: float, T: float, r: float, is_call: bool, max_iter: int = 100
    ) -> float:
        if price <= 0 or T <= 0:
            return 0.0

        low, high = 0.001, 5.0
        for _ in range(max_iter):
            mid = (low + high) / 2.0
            greeks = cls.calculate_greeks(F, K, T, r, mid, is_call)
            df = math.exp(-r * T)
            sqrt_t = math.sqrt(T)
            d1 = (math.log(F / K) + 0.5 * (mid**2) * T) / (mid * sqrt_t)
            d2 = d1 - mid * sqrt_t

            if is_call:
                calc_price = df * (F * norm.cdf(d1) - K * norm.cdf(d2))
            else:
                calc_price = df * (K * norm.cdf(-d2) - F * norm.cdf(-d1))

            diff = calc_price - price
            if abs(diff) < 1e-5:
                return mid

            if diff > 0:
                high = mid
            else:
                low = mid

        return (low + high) / 2.0