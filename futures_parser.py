import json
import pandas as pd


def parse_coffee_futures(file_path: str) -> pd.DataFrame:
    """Parsuje plik JSON z Barcharta zawierający historię kontraktu futures (OHLCV)."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_records = []

    def extract_records(node):
        if isinstance(node, dict):
            keys_lower = {str(k).lower(): k for k in node.keys()}
            if any(k in keys_lower for k in ["description", "field", "type"]) and "lastprice" not in keys_lower:
                return

            # Szukamy kluczy charakterystycznych dla świec Futures
            if any(k in keys_lower for k in ["lastprice", "open", "high", "low", "volume"]):
                raw_records.append(node)
                return

            for k, v in node.items():
                if k.lower() not in ("meta", "field", "type", "description"):
                    extract_records(v)

        elif isinstance(node, list):
            for elem in node:
                extract_records(elem)

    extract_records(data)

    parsed_rows = []

    def safe_float(val):
        if val is None or val == "":
            return None
        try:
            return float(str(val).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            return None

    for item in raw_records:
        for wrapper in ["raw", "attributes", "data"]:
            if isinstance(item.get(wrapper), dict):
                item = item[wrapper]

        item_map = {str(k).lower(): v for k, v in item.items()}

        def get_val(possible_keys):
            for k in possible_keys:
                if k.lower() in item_map and item_map[k.lower()] is not None:
                    return item_map[k.lower()]
            return None

        trade_time = get_val(["tradeTime", "trade_time", "time"])
        if not trade_time:
            continue

        parsed_rows.append({
            "trade_time": trade_time,
            "open": safe_float(get_val(["openPrice", "open"])),
            "high": safe_float(get_val(["highPrice", "high"])),
            "low": safe_float(get_val(["lowPrice", "low"])),
            "close": safe_float(get_val(["lastPrice", "close", "last"])),
            "volume": safe_float(get_val(["volume", "vol"])),
        })

    df = pd.DataFrame(parsed_rows)
    
    # Sortowanie chronologiczne i wywalenie pustych cen zamknięcia
    if not df.empty:
        df = df.dropna(subset=["close"])
        # Zakładamy, że najnowsza data jest na początku JSON-a, ale dla pewności odwracamy pod analizę
        # Zależnie od tego, jak Barchart sortuje JSON, poniższa linijka może wymagać dostosowania:
        # df = df.sort_values(by="trade_time", ascending=True).reset_index(drop=True)
    
    return df

def get_latest_spot(df_futures: pd.DataFrame) -> float:
    """Zwraca ostatnią znaną cenę zamknięcia z danych Futures."""
    if df_futures.empty:
        return 0.0
    
    # Bierzemy pierwszy wiersz (często najnowszy w Barchart JSON) lub ostatni, jeśli posortowano
    # Zakładając domyślne zachowanie tabeli Price History (od najnowszych):
    return float(df_futures.iloc[0]["close"])


if __name__ == "__main__":
    df_fut = parse_coffee_futures("coffee_futures.json")
    print(f"Pomyślnie załadowano {len(df_fut)} rekordów OHLCV.")
    if not df_fut.empty:
        print(df_fut.head(10))
        print(f"\n--- AKTUALNA CENA SPOT DO SILNIKA: {get_latest_spot(df_fut)} ---")