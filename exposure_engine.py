import os
import json
from typing import Optional

import numpy as np
import pandas as pd
from black76 import Black76Engine
from contract_specs import get_contract_spec


class OptionExposureCalculator:
    """Kalkulator ekspozycji rynkowych dealerów na bazie czystych, rzeczywistych danych."""

    def __init__(
        self,
        spot_price: float,
        risk_free_rate: float = 0.045,
        multiplier: Optional[float] = None,
        cache_dir: str = "data",
    ):
        self.spot = spot_price
        self.r = risk_free_rate
        # ``multiplier`` remains an optional legacy override. Without one,
        # select the contract size from the market passed to compute_exposures
        # (KC is the default market before the first calculation).
        self._multiplier_override = multiplier
        self.multiplier = (
            multiplier if multiplier is not None else get_contract_spec("KC").multiplier
        )
        self.cache_dir = cache_dir
        self.last_weighted_iv = 0.20
        self.last_delta_iv = 0.0
        
        os.makedirs(self.cache_dir, exist_ok=True)

    def _update_iv_state_per_strike(self, df_iv: pd.DataFrame, current_weighted_iv: float, ticker: str = "KC") -> dict:
        """Śledzi RZECZYWISTĄ zmienność z poprzedniego pliku JSON i liczy realne zmiany."""
        state_path = os.path.join(self.cache_dir, f"iv_state_{ticker}.json")
        prev_strikes_iv = {}
        prev_weighted_iv = current_weighted_iv

        if os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as sf:
                    s_data = json.load(sf)
                    prev_weighted_iv = float(s_data.get("weighted_iv", current_weighted_iv))
                    prev_strikes_iv = s_data.get("strikes_iv", {})
            except Exception:
                pass

        current_strikes_iv = {}
        delta_iv_map = {}

        for _, row in df_iv.iterrows():
            strike_str = f"{float(row['strike']):.2f}"
            iv_val = float(row["iv"])
            current_strikes_iv[strike_str] = iv_val

            prev_iv = prev_strikes_iv.get(strike_str, iv_val)
            delta_iv_map[strike_str] = iv_val - prev_iv

        try:
            with open(state_path, "w", encoding="utf-8") as sf:
                json.dump({
                    "weighted_iv": current_weighted_iv,
                    "strikes_iv": current_strikes_iv
                }, sf, indent=2)
        except Exception:
            pass

        self.last_delta_iv = current_weighted_iv - prev_weighted_iv
        return delta_iv_map

    def compute_exposures(
        self,
        df_options: pd.DataFrame,
        time_to_expiry_years: float,
        ticker: str = "KC"
    ) -> pd.DataFrame:
        spec = get_contract_spec(ticker)
        self.multiplier = (
            self._multiplier_override
            if self._multiplier_override is not None
            else spec.multiplier
        )

        df = df_options.copy()

        for col in ["gamma", "vanna", "charm", "vomma", "gex", "vex", "chex", "voex", "delta_iv", "vanna_flow"]:
            df[col] = 0.0

        for idx, row in df.iterrows():
            strike = float(row["strike"])
            is_call = str(row["option_type"]).upper() in ("CALL", "C")
            oi = float(row.get("open_interest", 0))
            mid_price = float(row.get("mid_price", 0.0))

            iv = float(row.get("iv", 0.0))
            if iv <= 0.001 and mid_price > 0:
                iv = Black76Engine.implied_volatility(
                    mid_price, self.spot, strike, time_to_expiry_years, self.r, is_call
                )

            df.at[idx, "iv"] = iv

            greeks = Black76Engine.calculate_greeks(
                self.spot, strike, time_to_expiry_years, self.r, iv, is_call
            )

            for greek_name in ["gamma", "vanna", "charm", "vomma"]:
                df.at[idx, greek_name] = greeks[greek_name]

            dealer_sign = 1.0 if is_call else -1.0

            df.at[idx, "gex"] = dealer_sign * greeks["gamma"] * oi * self.multiplier * 0.01 * (self.spot ** 2)
            df.at[idx, "vex"] = dealer_sign * greeks["vanna"] * oi * self.multiplier * self.spot * 0.01
            df.at[idx, "chex"] = dealer_sign * greeks["charm"] * oi * self.multiplier * self.spot
            
            # VOEX (Volga/Vomma Exposure) - wpływ zmiany IV na samą Vegę
            df.at[idx, "voex"] = dealer_sign * greeks["vomma"] * oi * self.multiplier

        valid_mask = (df["iv"] > 0.005) & (df["open_interest"] > 0)
        
        if valid_mask.any():
            weighted_iv = float(np.average(
                df.loc[valid_mask, "iv"], 
                weights=df.loc[valid_mask, "open_interest"]
            ))
        else:
            weighted_iv = float(df["iv"].mean()) if not df.empty else 0.20

        self.last_weighted_iv = weighted_iv

        delta_iv_map = self._update_iv_state_per_strike(
            df, weighted_iv, ticker=spec.ticker
        )

        for idx, row in df.iterrows():
            strike_str = f"{float(row['strike']):.2f}"
            d_iv = delta_iv_map.get(strike_str, 0.0)

            df.at[idx, "delta_iv"] = d_iv
            delta_iv_pp = d_iv * 100.0
            
            df.at[idx, "vanna_flow"] = -df.at[idx, "vex"] * delta_iv_pp

        return df

    def get_summary(self, df_processed: pd.DataFrame) -> dict:
        return {
            "spot_price": self.spot,
            "weighted_iv": self.last_weighted_iv,
            "delta_iv_pct": self.last_delta_iv * 100.0,
            "net_gex": float(df_processed["gex"].sum()),
            "net_vex": float(df_processed["vex"].sum()),
            "net_chex": float(df_processed["chex"].sum()),
            "net_voex": float(df_processed["voex"].sum()),
            "net_vanna_flow": float(df_processed["vanna_flow"].sum()),
            "regime": "POSITIVE_GAMMA" if df_processed["gex"].sum() >= 0 else "NEGATIVE_GAMMA",
        }

    @staticmethod
    def format_exposure_results(df_results: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        cols_to_show = [
            "strike", "option_type", "open_interest", "iv", "delta_iv", 
            "gex", "vex", "chex", "voex", "vanna_flow"
        ]
        
        df_top = df_results[cols_to_show].sort_values(by="open_interest", ascending=False).head(top_n).copy()
        df_formatted = pd.DataFrame()

        df_formatted["strike"] = df_top["strike"].map(lambda x: f"{x:.2f}")
        df_formatted["option_type"] = df_top["option_type"]
        df_formatted["open_interest"] = df_top["open_interest"].map(lambda x: f"{int(x):,}")
        df_formatted["iv"] = df_top["iv"].map(lambda x: f"{x:.4f}")
        df_formatted["delta_iv"] = df_top["delta_iv"].map(lambda x: f"{x*100:+.2f} pp")
        df_formatted["gex"] = df_top["gex"].map(lambda x: f"{x:,.2f}")
        df_formatted["vex"] = df_top["vex"].map(lambda x: f"{x:,.2f}")
        df_formatted["chex"] = df_top["chex"].map(lambda x: f"{x:,.2f}")
        df_formatted["voex"] = df_top["voex"].map(lambda x: f"{x:,.2f}")
        df_formatted["vanna_flow"] = df_top["vanna_flow"].map(lambda x: f"{x:,.2f}")

        return df_formatted

    @classmethod
    def print_exposure_report(cls, summary: dict, df_results: pd.DataFrame, top_n: int = 10):
        print("\n" + "=" * 130)
        print("=== PODSUMOWANIE EKSPOZYCJI OPCJI ===")
        print("=" * 130)

        for key, val in summary.items():
            if isinstance(val, float):
                print(f"{key:<20}: {val:>30,.2f}")
            else:
                print(f"{key:<20}: {val:>30}")

        print("\n" + "=" * 130)
        print(f"=== TOP {top_n} POZIOMÓW DRABINY EKSPOSYCJI ===")
        print("=" * 130)

        df_display = cls.format_exposure_results(df_results, top_n=top_n)
        print(df_display.to_string(index=False))
        print("=" * 130 + "\n")


if __name__ == "__main__":
    from contract_specs import get_contract_spec
    from options_parser import parse_options

    spec = get_contract_spec("KC")
    df_raw = parse_options(ticker=spec.ticker)

    if not df_raw.empty:
        CURRENT_SPOT = 285.15
        TIME_TO_EXPIRY = 0.15
        
        calc = OptionExposureCalculator(
            spot_price=CURRENT_SPOT, multiplier=spec.multiplier, cache_dir="data"
        )
        df_results = calc.compute_exposures(
            df_raw,
            time_to_expiry_years=TIME_TO_EXPIRY,
            ticker=spec.ticker
        )
        
        summary = calc.get_summary(df_results)
        calc.print_exposure_report(summary, df_results, top_n=10)