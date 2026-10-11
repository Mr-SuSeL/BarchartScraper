import math

import pandas as pd
import pytest

from exposure_engine import OptionExposureCalculator
from futures_parser import get_latest_spot, parse_coffee_futures
from coffee_parser import parse_coffee_options


@pytest.fixture
def sample_option_frame():
    return pd.DataFrame(
        [
            {'strike': 100.0, 'option_type': 'CALL', 'open_interest': 1000.0, 'mid_price': 5.75, 'iv': 0.20},
            {'strike': 100.0, 'option_type': 'PUT', 'open_interest': 850.0, 'mid_price': 5.75, 'iv': 0.20},
        ]
    )


def test_update_iv_state_per_strike_tracks_delta_iv(tmp_path):
    print("[INFO] Inicjalizacja kalkulatora i pierwszego stanu zmienności...")
    calc = OptionExposureCalculator(100.0, cache_dir=str(tmp_path))
    df = pd.DataFrame({'strike': [100.0, 105.0], 'iv': [0.20, 0.25]})

    first_delta = calc._update_iv_state_per_strike(df, 0.20, ticker='KC')
    assert first_delta == {'100.00': 0.0, '105.00': 0.0}
    assert (tmp_path / 'iv_state_KC.json').exists()

    print("[INFO] Aktualizacja zmienności i weryfikacja zmian dla każdego strike...")
    df_next = pd.DataFrame({'strike': [100.0, 105.0], 'iv': [0.22, 0.30]})
    second_delta = calc._update_iv_state_per_strike(df_next, 0.23, ticker='KC')

    assert second_delta['100.00'] == pytest.approx(0.02, rel=1e-9)
    assert second_delta['105.00'] == pytest.approx(0.05, rel=1e-9)
    assert calc.last_delta_iv == pytest.approx(0.03, rel=1e-9)


def test_compute_exposures_populates_greeks_and_exposure_columns(sample_option_frame, tmp_path):
    print("[INFO] Obliczanie greków i ekspozycji dla przykładowego łańcucha opcji...")
    calc = OptionExposureCalculator(100.0, risk_free_rate=0.05, cache_dir=str(tmp_path))

    result = calc.compute_exposures(sample_option_frame, time_to_expiry_years=1.0, ticker='KC')

    expected_cols = {
        'gamma', 'vanna', 'charm', 'vomma', 'gex', 'vex', 'chex', 'voex', 'delta_iv', 'vanna_flow'
    }
    assert expected_cols.issubset(result.columns)
    assert result['gex'].iloc[0] > 0.0
    assert result['gex'].iloc[1] < 0.0
    assert result['vex'].iloc[0] > 0.0
    assert result['vex'].iloc[1] < 0.0
    assert math.isfinite(result['vanna_flow'].sum())

    print("[INFO] Weryfikacja podsumowania i reżimu GEX...")
    summary = calc.get_summary(result)
    assert summary['regime'] == 'POSITIVE_GAMMA'
    assert summary['net_gex'] > 0.0
    assert summary['net_vanna_flow'] >= 0.0


def test_format_exposure_results_renders_readable_strings(sample_option_frame, tmp_path):
    print("[INFO] Obliczanie i formatowanie wyników ekspozycji...")
    calc = OptionExposureCalculator(100.0, risk_free_rate=0.05, cache_dir=str(tmp_path))
    result = calc.compute_exposures(sample_option_frame, time_to_expiry_years=1.0, ticker='KC')

    formatted = calc.format_exposure_results(result, top_n=2)

    assert 'strike' in formatted.columns
    assert 'option_type' in formatted.columns
    assert 'gex' in formatted.columns
    assert 'vex' in formatted.columns
    assert 'delta_iv' in formatted.columns
    assert formatted.shape[0] == 2
    assert 'CALL' in formatted['option_type'].tolist()
    assert 'PUT' in formatted['option_type'].tolist()


def test_compute_exposures_uses_stateful_iv_deltas_between_runs(tmp_path):
    print("[INFO] Obliczanie ekspozycji dla początkowego zestawu opcji...")
    calc = OptionExposureCalculator(100.0, risk_free_rate=0.05, cache_dir=str(tmp_path))

    initial = pd.DataFrame([
        {'strike': 100.0, 'option_type': 'CALL', 'open_interest': 1000.0, 'mid_price': 5.75, 'iv': 0.20},
        {'strike': 105.0, 'option_type': 'PUT', 'open_interest': 500.0, 'mid_price': 4.50, 'iv': 0.18},
    ])
    first_run = calc.compute_exposures(initial, time_to_expiry_years=1.0, ticker='KC')
    assert first_run['delta_iv'].tolist() == [0.0, 0.0]

    print("[INFO] Ponowne obliczanie po zmianie IV i weryfikacja przepływu vanna...")
    updated = pd.DataFrame([
        {'strike': 100.0, 'option_type': 'CALL', 'open_interest': 1000.0, 'mid_price': 5.95, 'iv': 0.23},
        {'strike': 105.0, 'option_type': 'PUT', 'open_interest': 500.0, 'mid_price': 4.80, 'iv': 0.22},
    ])
    second_run = calc.compute_exposures(updated, time_to_expiry_years=1.0, ticker='KC')

    assert second_run['delta_iv'].iloc[0] == pytest.approx(0.03, rel=1e-9)
    assert second_run['delta_iv'].iloc[1] == pytest.approx(0.04, rel=1e-9)
    assert second_run['vanna_flow'].iloc[0] != pytest.approx(0.0, abs=1e-12)


def test_coffee_profile_vex_uses_market_scale_and_is_plotted_as_vanna(
    coffee_options_json_path, coffee_futures_json_path, tmp_path
):
    print("[INFO] Parsowanie profilu kawy i pobieranie ceny spot...")
    options = parse_coffee_options(str(coffee_options_json_path))
    futures = parse_coffee_futures(str(coffee_futures_json_path))
    spot = get_latest_spot(futures)

    print("[INFO] Obliczanie ekspozycji VEX dla kontraktu KC...")
    calc = OptionExposureCalculator(spot, cache_dir=str(tmp_path))
    result = calc.compute_exposures(options, time_to_expiry_years=0.15, ticker="KC")

    expected_vex = (
        result["vanna"]
        * result["open_interest"]
        * calc.multiplier
        * spot
        * 0.01
        * result["option_type"].str.upper().isin(("CALL", "C")).map({True: 1.0, False: -1.0})
    )
    assert result["vex"].tolist() == pytest.approx(expected_vex.tolist())
    assert result["vex"].abs().max() >= 1_000_000.0

    print("[INFO] Weryfikacja panelu VEX i układu wykresu...")
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from visualize_exposures import plot_exposures_dashboard

    summary = calc.get_summary(result)
    figure = plot_exposures_dashboard(
        result,
        summary,
        out_file=str(tmp_path / "coffee_vex.png"),
    )
    try:
        titled_axes = [axis for axis in figure.axes if axis.get_title()]
        axes_by_title = {axis.get_title(): axis for axis in titled_axes}
        expected_titles = (
            "GEX (Gamma Exposure",
            "VEX (Vanna Exposure",
            "VOEX (Volga/Vomma Exposure",
            "CHEX (Charm Exposure",
            "VANNA FLOW (",
            "RZECZYWISTA KRZYWA IV ORAZ LOKALNA",
        )
        for title_prefix in expected_titles:
            assert any(title.startswith(title_prefix) for title in axes_by_title)
        assert len(titled_axes) == 6

        # Three equal-width panels per row; the IV profile is the third panel,
        # rather than spanning multiple columns.
        ordered_axes = sorted(
            titled_axes,
            key=lambda axis: (-axis.get_position().y0, axis.get_position().x0),
        )
        top_row, bottom_row = ordered_axes[:3], ordered_axes[3:]
        assert len(top_row) == len(bottom_row) == 3
        assert tuple(axis.get_title().split(" (")[0] for axis in top_row) == (
            "GEX",
            "VEX",
            "VOEX",
        )
        assert tuple(axis.get_title().split(" (")[0] for axis in bottom_row) == (
            "CHEX",
            "VANNA FLOW",
            "RZECZYWISTA KRZYWA IV ORAZ LOKALNA ΔIV",
        )
        for row in (top_row, bottom_row):
            positions = [axis.get_position() for axis in row]
            assert [position.x0 for position in positions] == sorted(
                position.x0 for position in positions
            )
            assert positions[0].y0 == pytest.approx(positions[1].y0)
            assert positions[1].y0 == pytest.approx(positions[2].y0)
            assert positions[0].width == pytest.approx(positions[1].width)
            assert positions[1].width == pytest.approx(positions[2].width)
            assert positions[0].x1 < positions[1].x0
            assert positions[1].x1 < positions[2].x0

        # Every panel keeps a legible y-axis label, including both IV scales.
        for axis in titled_axes:
            assert axis.get_ylabel().strip()
            assert axis.yaxis.label.get_fontsize() >= 8
        iv_axis = next(
            axis
            for axis in titled_axes
            if axis.get_title().startswith("RZECZYWISTA KRZYWA IV")
        )
        assert iv_axis.get_ylabel() == "Implied Volatility [%]"
        secondary_iv_axis = next(axis for axis in figure.axes if axis not in titled_axes)
        assert secondary_iv_axis.get_ylabel() == "Local ΔIV [pp]"
        assert secondary_iv_axis.yaxis.label.get_fontsize() >= 8

        vex_axis = next(axis for axis in titled_axes if axis.get_title().startswith("VEX (Vanna Exposure"))
        vex_bars = [bar.get_height() for bar in vex_axis.patches]
        vex_by_strike = result.groupby("strike")["vex"].sum()
        visible_vex = vex_by_strike[
            (vex_by_strike.index >= spot * 0.75)
            & (vex_by_strike.index <= spot * 1.25)
        ] / 1e6
        assert vex_bars
        assert vex_bars == pytest.approx(visible_vex.tolist())
    finally:
        plt.close(figure)
