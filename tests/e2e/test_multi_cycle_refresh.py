import asyncio
import json
import os
import shutil
import sys
import types
from pathlib import Path

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

stub_playwright = types.ModuleType("playwright")
stub_async_api = types.ModuleType("playwright.async_api")


class _StubAsyncPlaywright:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __call__(self, *args, **kwargs):
        return self

    def chromium(self):
        return self

    async def launch(self, *args, **kwargs):
        return self

    async def new_context(self, *args, **kwargs):
        return self

    async def new_page(self, *args, **kwargs):
        return self

    async def goto(self, *args, **kwargs):
        return None

    async def close(self, *args, **kwargs):
        return None

    async def route(self, *args, **kwargs):
        return None

    def on(self, *args, **kwargs):
        return None


stub_async_api.async_playwright = _StubAsyncPlaywright()
stub_playwright.async_api = stub_async_api
sys.modules.setdefault("playwright", stub_playwright)
sys.modules.setdefault("playwright.async_api", stub_async_api)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

import run_pipeline
from futures_parser import get_latest_spot, parse_futures


def test_pipeline_refresh_detects_iv_change_and_updates_vanna_flow(monkeypatch, tmp_path):
    print("[INFO] Kopiowanie cache'owanych danych futures i opcji...")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for filename in ("kc_futures.json", "kc_options.json"):
        shutil.copy2(ROOT / "data" / filename, data_dir / filename)
    monkeypatch.chdir(tmp_path)

    async def fake_scrape(ticker="KC"):
        assert ticker == "KC"
        return None

    monkeypatch.setattr(run_pipeline, "scrape_options", fake_scrape)
    monkeypatch.setattr(run_pipeline, "scrape_futures", fake_scrape)

    original_parse_options = run_pipeline.parse_options
    parse_cycles = 0

    def parse_options_with_cycle_iv(path=None, ticker="KC"):
        nonlocal parse_cycles
        options = original_parse_options(path, ticker=ticker)
        parse_cycles += 1
        options["iv"] = 0.20 + (0.02 if parse_cycles > 1 else 0.0)
        return options

    monkeypatch.setattr(run_pipeline, "parse_options", parse_options_with_cycle_iv)

    plot_summaries = []
    plot_flow_bars = []
    plotted_results = []
    original_plot = run_pipeline.plot_exposures_dashboard

    def capture_plot(df_results, summary, fig=None, **kwargs):
        figure = original_plot(df_results, summary, fig=fig, **kwargs)
        plot_summaries.append(summary.copy())
        plotted_results.append(df_results.copy())
        flow_axis = next(
            axis for axis in figure.axes
            if axis.get_title().startswith("VANNA FLOW")
        )
        plot_flow_bars.append([bar.get_height() for bar in flow_axis.patches])
        return figure

    monkeypatch.setattr(run_pipeline, "plot_exposures_dashboard", capture_plot)

    futures = parse_futures(str(data_dir / "kc_futures.json"))
    spot = get_latest_spot(futures)
    assert spot > 0
    state_file = data_dir / "iv_state_KC.json"

    print("[INFO] Uruchamianie pierwszego cyklu z IV bazową...")
    figure = asyncio.run(run_pipeline.run_single_cycle(None))
    try:
        assert state_file.exists()
        with state_file.open("r", encoding="utf-8") as state_handle:
            first_state = json.load(state_handle)
        assert first_state["strikes_iv"]
        assert set(first_state["strikes_iv"].values()) == {0.20}
        assert plot_summaries[0]["delta_iv_pct"] == pytest.approx(0.0)
        assert plot_summaries[0]["net_vanna_flow"] == pytest.approx(0.0)

        print("[INFO] Uruchamianie drugiego cyklu po wzroście IV o 0.02...")
        figure = asyncio.run(run_pipeline.run_single_cycle(figure))

        with state_file.open("r", encoding="utf-8") as state_handle:
            second_state = json.load(state_handle)
        assert set(second_state["strikes_iv"].values()) == {0.22}
        assert plot_summaries[1]["delta_iv_pct"] == pytest.approx(2.0)
        assert plotted_results[1]["delta_iv"].tolist() == pytest.approx(
            [0.02] * len(plotted_results[1])
        )
        assert plotted_results[1]["vanna_flow"].abs().sum() > 0
        assert plot_summaries[1]["net_vanna_flow"] != pytest.approx(0.0)
        assert plot_flow_bars[1]
        assert any(value != pytest.approx(0.0) for value in plot_flow_bars[1])
        assert (tmp_path / "dashboards" / "kc_exposures_dashboard.png").exists()
    finally:
        if figure is not None:
            plt.close(figure)
