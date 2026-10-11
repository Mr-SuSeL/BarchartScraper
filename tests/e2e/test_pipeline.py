import asyncio
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

import run_pipeline


def test_run_single_cycle_uses_cached_fixture_data(monkeypatch, tmp_path):
    print("[INFO] Kopiowanie plików fixture do katalogu tymczasowego...")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for filename in ("kc_futures.json", "kc_options.json"):
        shutil.copy2(ROOT / "data" / filename, data_dir / filename)

    print("[INFO] Przygotowanie atrap scrapingu i wykresu...")
    monkeypatch.chdir(tmp_path)

    calls = {"options": 0, "futures": 0}

    async def fake_scrape_options(ticker="KC"):
        assert ticker == "KC"
        calls["options"] += 1

    async def fake_scrape_futures(ticker="KC"):
        assert ticker == "KC"
        calls["futures"] += 1

    monkeypatch.setattr(run_pipeline, "scrape_options", fake_scrape_options)
    monkeypatch.setattr(run_pipeline, "scrape_futures", fake_scrape_futures)

    class DummyFigure:
        number = 42

    def fake_plot(df_results, summary, fig=None, **kwargs):
        assert not df_results.empty
        assert summary["spot_price"] == pytest.approx(286.95)
        return DummyFigure()

    monkeypatch.setattr(run_pipeline, "plot_exposures_dashboard", fake_plot)

    print("[INFO] Uruchamianie pojedynczego cyklu pipeline'u...")
    fig_handle = asyncio.run(run_pipeline.run_single_cycle(None))

    assert fig_handle is not None
    assert fig_handle.number == 42
    assert calls == {"options": 1, "futures": 1}

    print("[INFO] Parsowanie lokalnych danych futures i opcji...")
    df_futures = run_pipeline.parse_futures("data/kc_futures.json")
    df_options = run_pipeline.parse_options("data/kc_options.json")

    assert len(df_futures) > 0
    assert len(df_options) > 0

    print("[INFO] Weryfikacja ceny spot...")
    spot_price = run_pipeline.get_latest_spot(df_futures)
    assert spot_price == pytest.approx(286.95)

    print("[INFO] Obliczanie ekspozycji opcji...")
    calc = run_pipeline.OptionExposureCalculator(
        spot_price=spot_price,
        multiplier=run_pipeline.get_contract_spec("KC").multiplier,
        cache_dir="data",
    )
    df_results = calc.compute_exposures(df_options, time_to_expiry_years=0.15, ticker="KC")
    summary = calc.get_summary(df_results)

    print("[INFO] Weryfikacja podsumowania i reżimu GEX...")
    assert summary["spot_price"] == pytest.approx(spot_price)
    assert summary["weighted_iv"] > 0.0
    assert summary["regime"] in {"NEGATIVE_GAMMA", "POSITIVE_GAMMA"}
    assert "net_gex" in summary
