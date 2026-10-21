import json, os, math, datetime
import yfinance as yf

TICKERS = [
    ("gold", "GC=F", "Gold", "oz", "Precious metals"),
    ("silver", "SI=F", "Silver", "oz", "Precious metals"),
    ("platinum", "PL=F", "Platinum", "oz", "Precious metals"),
    ("palladium", "PA=F", "Palladium", "oz", "Precious metals"),
    ("copper", "HG=F", "Copper", "lb", "Industrial metals"),
    ("brent", "BZ=F", "Brent Crude", "bbl", "Energy"),
    ("wti", "CL=F", "WTI Crude", "bbl", "Energy"),
    ("natgas", "NG=F", "Natural Gas", "MMBtu", "Energy"),
]
FX = "EURUSD=X"


def num(v, dp):
    v = float(v)
    return None if math.isnan(v) else round(v, dp)


os.makedirs("data", exist_ok=True)
symbols = [t[1] for t in TICKERS] + [FX]
raw = yf.download(symbols, period="max", interval="1d", progress=False, auto_adjust=False)["Close"].sort_index()
full = raw.ffill()

eurusd = float(raw[FX].dropna().iloc[-1])
now = datetime.datetime.now(datetime.timezone.utc)
items = []

for key, sym, name, unit, group in TICKERS:
    s = raw[sym].dropna()
    if len(s) < 2:
        print("No data for", sym)
        continue
    price = float(s.iloc[-1])
    prev = float(s.iloc[-2])
    items.append({
        "key": key, "name": name, "unit": unit, "group": group,
        "usd": round(price, 4),
        "eur": round(price / eurusd, 4),
        "change_pct": round((price - prev) / prev * 100, 2),
    })
    print(name, "history from", s.index[0].strftime("%Y-%m-%d"))

with open("data/latest.json", "w") as f:
    json.dump({"updated": now.isoformat(), "eurusd": eurusd, "items": items}, f, indent=1)

hist = {
    "dates": [d.strftime("%Y-%m-%d") for d in full.index],
    "eurusd": [num(v, 5) for v in full[FX]],
    "series": {},
}
for key, sym, name, unit, group in TICKERS:
    hist["series"][key] = [num(v, 4) for v in full[sym]]

with open("data/history.json", "w") as f:
    json.dump(hist, f, separators=(",", ":"))

print("Saved", len(items), "prices,", len(hist["dates"]), "days of history")
