import json
from pathlib import Path

import pandas as pd

from contract_specs import get_contract_spec


def parse_options(file_path: str | Path | None = None, ticker: str = "KC") -> pd.DataFrame:
    """Parse generic Barchart options data from a ticker-specific JSON file."""
    spec = get_contract_spec(ticker)
    if file_path is None:
        file_path = Path("data") / f"{spec.ticker.lower()}_options.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_records = []

    # Rekurencyjne szukanie słowników zawierających dane opcji
    def extract_records(node):
        if isinstance(node, dict):
            keys_lower = {str(k).lower(): k for k in node.keys()}

            # Odrzucamy słowniki z metadanymi / opisami pól
            if any(k in keys_lower for k in ["description", "field", "type"]) and "strikeprice" not in keys_lower:
                return

            # Sprawdzamy czy ten słownik zawiera kluczowe pola dla opcji
            if any(k in keys_lower for k in ["strikeprice", "strike", "openinterest", "lastprice", "optiontype"]):
                raw_records.append(node)
                return

            # Jeśli nie, przeszukujemy jego wartości
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

    def safe_int(val):
        res = safe_float(val)
        return int(res) if res is not None else 0

    for item in raw_records:
        # Rozpakowanie zagnieżdżeń typu 'raw' / 'attributes'
        for wrapper in ["raw", "attributes", "data"]:
            if isinstance(item.get(wrapper), dict):
                item = item[wrapper]

        item_map = {str(k).lower(): v for k, v in item.items()}

        def get_val(possible_keys):
            for k in possible_keys:
                if k.lower() in item_map and item_map[k.lower()] is not None:
                    return item_map[k.lower()]
            return None

        strike_val = get_val(["strikePrice", "strike", "strike_price", "strikepriceraw"])
        strike = safe_float(strike_val)

        if strike is None:
            continue

        open_interest = safe_int(get_val(["openInterest", "open_interest", "openinterestraw"]))
        volume = safe_int(get_val(["volume", "vol", "volumeraw"]))
        last_price = safe_float(get_val(["lastPrice", "last_price", "last", "lastpriceraw"]))
        bid = safe_float(get_val(["bidPrice", "bid_price", "bid", "bidpriceraw"]))
        ask = safe_float(get_val(["askPrice", "ask_price", "ask", "askpriceraw"]))
        opt_type = str(get_val(["optionType", "option_type", "type", "symbolType"]) or "").upper()
        trade_time = get_val(["tradeTime", "trade_time", "time"])
        symbol = get_val(["symbol", "longSymbol", "symbolCode", "long_symbol"])

        # Wyliczenie Mid Price
        if bid is not None and ask is not None and (bid + ask) > 0:
            mid_price = (bid + ask) / 2.0
        else:
            mid_price = last_price

        parsed_rows.append({
            "strike": strike,
            "option_type": opt_type,
            "open_interest": open_interest,
            "volume": volume,
            "last_price": last_price,
            "bid": bid,
            "ask": ask,
            "mid_price": mid_price,
            "trade_time": trade_time,
            "symbol": symbol
        })

    if not parsed_rows:
        print("DIAGNOSTYKA: Nie znaleziono rekordów opcji. Klucze głównego obiektu JSON:")
        if isinstance(data, dict):
            print(list(data.keys())[:20])
        return pd.DataFrame()

    df = pd.DataFrame(parsed_rows)

    # Filtrowanie aktywnych opcji (OI > 0 lub Volume > 0)
    df_active = df[(df["open_interest"] > 0) | (df["volume"] > 0)].reset_index(drop=True)

    return df_active


if __name__ == "__main__":
    df_options = parse_options()
    print(f"Pomyślnie załadowano {len(df_options)} aktywnych rekordów opcji.")
    if not df_options.empty:
        print(df_options[["strike", "option_type", "open_interest", "volume", "mid_price", "symbol"]].head(15))