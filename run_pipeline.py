import argparse
import asyncio
import time
from datetime import datetime
import matplotlib.pyplot as plt

# Wymuszenie ciemnego stylu w pętli głównej
plt.style.use("dark_background")

from contract_specs import TICKER_MAPPER, get_contract_spec
from options_scraper import scrape_options
from futures_scraper import scrape_futures
from options_parser import parse_options
from futures_parser import parse_futures, get_latest_spot
from exposure_engine import OptionExposureCalculator
from visualize_exposures import plot_exposures_dashboard


async def run_single_cycle(fig_handle, ticker="KC"):
    """Wykonuje jeden pełny cykl: pobranie, parsowanie, matma i odświeżenie okna."""
    spec = get_contract_spec(ticker)
    ticker = spec.ticker
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 1. Pobieranie drabiny opcji...")
    await scrape_options(ticker)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 2. Pobieranie historii futures...")
    await scrape_futures(ticker)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 3. Przetwarzanie danych i przeliczanie silnika...")
    df_options = parse_options(ticker=ticker)
    df_futures = parse_futures(ticker=ticker)
    spot_price = get_latest_spot(df_futures)

    if df_options.empty or spot_price <= 0:
        print("[!] Błąd: Brak prawidłowych danych z Barchart. Pomijam przerysowanie.")
        return fig_handle

    calc = OptionExposureCalculator(
        spot_price=spot_price, multiplier=spec.multiplier, cache_dir="data"
    )
    df_results = calc.compute_exposures(df_options, time_to_expiry_years=0.15, ticker=ticker)
    summary = calc.get_summary(df_results)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 4. Odświeżanie interaktywnego wykresu (Spot: {spot_price})...")
    fig_handle = plot_exposures_dashboard(
        df_results, summary=summary, fig=fig_handle, ticker=ticker
    )

    return fig_handle


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Barchart options exposure pipeline")
    parser.add_argument(
        "--ticker",
        default="KC",
        type=str.upper,
        choices=tuple(TICKER_MAPPER),
        help="Supported futures ticker (default: KC)",
    )
    return parser.parse_args(argv)


async def main(ticker="KC"):
    INTERVAL_MINUTES = 15
    INTERVAL_SECONDS = INTERVAL_MINUTES * 60

    print("=" * 70)
    print(" 🚀 OPTIONS MICROSTRUCTURE PIPELINE (LIVE UI)")
    print("=" * 70)
    print(f"Pętla pracuje w tle. Wykres będzie aktualizowany co {INTERVAL_MINUTES} minut.")
    print("Możesz swobodnie przybliżać/przesuwać okno wykresu.\n")

    fig_handle = None

    while True:
        start_time = time.time()
        try:
            fig_handle = await run_single_cycle(fig_handle, ticker=ticker)
        except Exception as e:
            print(f"[!] Błąd w cyklu: {e}")

        elapsed = time.time() - start_time
        print(f"✔ Cykl zakończony w {elapsed:.2f} s. Następne odświeżenie za {INTERVAL_MINUTES} min.")

        # Tryb cichy (nie miga na pasku zadań):
        sleep_steps = int(INTERVAL_SECONDS)
        for _ in range(sleep_steps):
            if fig_handle and plt.fignum_exists(fig_handle.number):
                fig_handle.canvas.flush_events()  # Obsługa myszki/zoomu bez wymuszania focusu
            await asyncio.sleep(1.0)  # Asynchroniczne uśpienie pętli


if __name__ == "__main__":
    try:
        asyncio.run(main(ticker=parse_args().ticker))
    except KeyboardInterrupt:
        print("\n[+] Zatrzymano robota na żądanie użytkownika.")