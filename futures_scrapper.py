import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright

async def scrape_futures():
    print("[+] Uruchamianie szybkiego Playwright (Futures)...")
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
        
        # BLOKOWANIE ŚMIECI
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,eot,mp4,webp}", lambda route: route.abort())

        captured_json = []

        async def handle_response(response):
            url = response.url
            if ("historical" in url or "proxies" in url) and response.status == 200:
                try:
                    data = await response.json()
                    if isinstance(data, dict) and "data" in data and data["data"]:
                        print(f"[+] Przechwycono API Futures!")
                        captured_json.append(data)
                except Exception:
                    pass

        page.on("response", handle_response)

        target_url = "https://www.barchart.com/futures/quotes/KCZ26/price-history/historical"
        print(f"[+] Ładowanie strony futures...")
        
        try:
            await page.goto(target_url, wait_until="commit", timeout=30000)
            
            # Czekamy tylko na przechwycenie danych
            for _ in range(24):
                if captured_json:
                    break
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[!] Info: {e}")

        await browser.close()

        if captured_json:
            res_data = captured_json[-1]
            with open("coffee_futures.json", "w", encoding="utf-8") as f:
                json.dump(res_data, f, indent=4, ensure_ascii=False)

            data_content = res_data.get("data", [])
            rows = [item.get("raw", item) for item in data_content if isinstance(data_content, list)]

            if rows:
                df = pd.DataFrame(rows)
                df.to_csv("coffee_futures.csv", index=False)
                print(f"[+] Pomyślnie pobrano {len(df)} rekordów futures.")
        else:
            print("[-] Nie przechwycono futures.")

if __name__ == "__main__":
    asyncio.run(scrape_futures())