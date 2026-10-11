import asyncio
import time
from datetime import datetime
import matplotlib.pyplot as plt

# Wymuszenie ciemnego stylu w pętli głównej
plt.style.use("dark_background")

from coffee import scrape_options
from futures_scrapper import scrape_futures
from coffee_parser import parse_coffee_options
from futures_parser import parse_coffee_futures, get_latest_spot
from exposure_engine import OptionExposureCalculator
from visualize_exposures import plot_exposures_dashboard


async def run_single_cycle(fig_handle):
    """Wykonuje jeden pełny cykl: pobranie, parsowanie, matma i odświeżenie okna."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 1. Pobieranie drabiny opcji...")
    await scrape_options()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 2. Pobieranie historii futures...")
    await scrape_futures()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 3. Przetwarzanie danych i przeliczanie silnika...")
    df_options = parse_coffee_options("coffee_options.json")
    df_futures = parse_coffee_futures("coffee_futures.json")
    spot_price = get_latest_spot(df_futures)

    if df_options.empty or spot_price <= 0:
        print("[!] Błąd: Brak prawidłowych danych z Barchart. Pomijam przerysowanie.")
        return fig_handle

    calc = OptionExposureCalculator(spot_price=spot_price, multiplier=37500.0, cache_dir="cache")
    df_results = calc.compute_exposures(df_options, time_to_expiry_years=0.15, ticker="KC")
    summary = calc.get_summary(df_results)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 4. Odświeżanie interaktywnego wykresu (Spot: {spot_price})...")
    fig_handle = plot_exposures_dashboard(df_results, summary=summary, fig=fig_handle)

    return fig_handle


async def main():
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
            fig_handle = await run_single_cycle(fig_handle)
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
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[+] Zatrzymano robota na żądanie użytkownika.")