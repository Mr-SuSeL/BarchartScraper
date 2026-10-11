import asyncio
import json
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright


from contract_specs import get_contract_spec


def build_options_url(ticker: str = "KC") -> str:
    """Build the Barchart options URL for a supported continuous contract."""
    spec = get_contract_spec(ticker)
    return (
        f"https://www.barchart.com/futures/quotes/"
        f"{spec.barchart_symbol}/options?mode=d&view=stacked"
    )


async def scrape_options(ticker: str = "KC"):
    spec = get_contract_spec(ticker)
    ticker = spec.ticker
    print("[+] Uruchamianie szybkiego Playwright (Opcje)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        # BLOKOWANIE ŚMIECI (Obrazki, style, czcionki, media)
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,eot,mp4,webp}", lambda route: route.abort())

        captured_json = []

        async def handle_response(response):
            url = response.url
            if ("options" in url or "proxies" in url) and response.status == 200:
                try:
                    data = await response.json()
                    if isinstance(data, dict) and "data" in data and data["data"]:
                        print(f"[+] Przechwycono API Opcji!")
                        captured_json.append(data)
                except Exception:
                    pass

        page.on("response", handle_response)

        target_url = build_options_url(ticker)
        print(f"[+] Ładowanie strony opcji...")
        
        try:
            # Nie czekamy na pełny DOM, wchodzimy od razu
            await page.goto(target_url, wait_until="commit", timeout=30000)
            
            # Czekamy pętlą tylko do momentu przechwycenia JSON-a (maksymalnie 12 sekund)
            for _ in range(24):
                if captured_json:
                    break
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[!] Info: {e}")

        await browser.close()

        if captured_json:
            res_data = captured_json[0]
            data_dir = Path("data")
            data_dir.mkdir(parents=True, exist_ok=True)
            options_file = data_dir / f"{ticker.lower()}_options.json"
            with options_file.open("w", encoding="utf-8") as f:
                json.dump(res_data, f, indent=4, ensure_ascii=False)

            data_content = res_data.get("data", {})
            rows = []
            if isinstance(data_content, dict):
                for option_type, items in data_content.items():
                    if isinstance(items, list):
                        for item in items:
                            rows.append(item.get("raw", item))
            elif isinstance(data_content, list):
                for item in data_content:
                    rows.append(item.get("raw", item))

            if rows:
                df = pd.DataFrame(rows)
                df.to_csv(data_dir / f"{ticker.lower()}_options.csv", index=False)
                print(f"[+] Pomyślnie pobrano {len(df)} opcji.")
        else:
            print("[-] Nie przechwycono opcji.")

if __name__ == "__main__":
    asyncio.run(scrape_options())