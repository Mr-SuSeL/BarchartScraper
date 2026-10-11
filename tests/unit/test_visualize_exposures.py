import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from visualize_exposures import plot_exposures_dashboard


@pytest.mark.parametrize(
    ("strikes", "expected_width"),
    [
        ([100.0, 100.1, 100.2, 100.3], 0.07),
        ([100.0, 105.0, 110.0], 3.5),
    ],
)
def test_dashboard_bars_scale_to_strike_spacing_and_keep_padding(
    strikes, expected_width, tmp_path
):
    frame = pd.DataFrame(
        {
            "strike": strikes,
            "gex": [1.0, -2.0, 3.0, -4.0][: len(strikes)],
            "vex": [1.0, -2.0, 3.0, -4.0][: len(strikes)],
            "voex": [1.0, -2.0, 3.0, -4.0][: len(strikes)],
            "chex": [1.0, -2.0, 3.0, -4.0][: len(strikes)],
            "vanna_flow": [1.0, -2.0, 3.0, -4.0][: len(strikes)],
            "iv": [0.2] * len(strikes),
            "delta_iv": [0.01, -0.02, 0.03, -0.04][: len(strikes)],
        }
    )
    summary = {
        "spot_price": float(np.mean(strikes)),
        "delta_iv_pct": 0.0,
        "weighted_iv": 0.2,
    }

    figure = plot_exposures_dashboard(
        frame,
        summary,
        ticker="SB",
        out_file=str(tmp_path / "dashboard.png"),
    )
    try:
        assert figure._suptitle is not None
        assert figure._suptitle.get_text().startswith("Greeks Analytics:")
        axes_by_title = {axis.get_title(): axis for axis in figure.axes if axis.get_title()}
        for prefix in ("GEX", "VEX", "VOEX", "CHEX", "VANNA FLOW"):
            axis = next(
                axis for title, axis in axes_by_title.items() if title.startswith(prefix)
            )
            bars = axis.patches
            assert [bar.get_width() for bar in bars] == pytest.approx(
                [expected_width] * len(strikes)
            )
            assert all(bar.get_facecolor()[3] == pytest.approx(0.7) for bar in bars)
            assert all(bar.get_edgecolor()[3] == pytest.approx(0.65) for bar in bars)
            ordered_bars = sorted(bars, key=lambda bar: bar.get_x())
            assert all(
                left.get_x() + left.get_width() <= right.get_x() + 1e-12
                for left, right in zip(ordered_bars, ordered_bars[1:])
            )

        iv_axis = next(
            axis for title, axis in axes_by_title.items() if title.startswith("RZECZYWISTA")
        )
        secondary_iv_axis = next(axis for axis in figure.axes if axis not in axes_by_title.values())
        expected_padding = max(
            (max(strikes) - min(strikes)) * 0.05,
            expected_width * 0.55,
        )
        expected_xlim = (min(strikes) - expected_padding, max(strikes) + expected_padding)
        assert iv_axis.get_xlim() == pytest.approx(expected_xlim)
        assert secondary_iv_axis.get_xlim() == pytest.approx(expected_xlim)
        for axis in figure.axes:
            assert axis.get_xlim() == pytest.approx(expected_xlim)

        iv_delta_bars = secondary_iv_axis.patches
        assert [bar.get_width() for bar in iv_delta_bars] == pytest.approx(
            [expected_width] * len(strikes)
        )
        assert all(
            bar.get_facecolor()[3] == pytest.approx(0.6)
            for bar in iv_delta_bars
        )
        assert all(
            bar.get_edgecolor()[3] == pytest.approx(0.65)
            for bar in iv_delta_bars
        )
    finally:
        plt.close(figure)


def test_strike_bar_width_falls_back_for_fewer_than_two_unique_strikes():
    from visualize_exposures import _get_strike_bar_width

    assert _get_strike_bar_width([]) == pytest.approx(0.5)
    assert _get_strike_bar_width([100.0]) == pytest.approx(0.5)
    assert _get_strike_bar_width([100.0, 100.0]) == pytest.approx(0.5)
