import json, datetime
from ai import chat, news

QUERIES = [
    ("Gold", "gold price"),
    ("Silver", "silver price"),
    ("Platinum and palladium", "platinum palladium price"),
    ("Copper", "copper price"),
    ("Oil", "oil prices"),
    ("Natural gas", "natural gas prices"),
]


def pct(v):
    return "n/a" if v is None else "%+.2f%%" % v


def change(hist, key, rows):
    s = [v for v in hist["series"][key] if v is not None]
    if len(s) <= rows:
        return None
    base = s[-1 - rows]
    return round((s[-1] - base) / abs(base) * 100, 2)


def main():
    with open("data/latest.json") as f:
        latest = json.load(f)
    with open("data/history.json") as f:
        hist = json.load(f)

    lines = []
    for it in latest["items"]:
        k = it["key"]
        lines.append("%s: $%.2f per %s (EUR %.2f) | day %s | week %s | month %s | year %s" % (
            it["name"], it["usd"], it["unit"], it["eur"], pct(it["change_pct"]),
            pct(change(hist, k, 5)), pct(change(hist, k, 22)), pct(change(hist, k, 261))))

    heads, refs = [], []
    for label, q in QUERIES:
        items = news(q + " when:1d", 5)
        if not items:
            continue
        heads.append(label + ":")
        for n in items:
            refs.append(n)
            heads.append("[%d] %s" % (len(refs), n["title"]))

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%A %d %B %Y")
    prompt = (
        "You are a commodities market analyst writing a short daily briefing for a business owner in Ireland. "
        "Today is " + today + ". Closing prices (front-month futures settlements):\n" + "\n".join(lines)
        + "\nEUR/USD: %.4f\n\n" % latest["eurusd"]
        + "News headlines from the last 24 hours:\n" + ("\n".join(heads) if heads else "(none available)") + "\n\n"
        "Write the briefing.\n"
        "Rules:\n"
        "- First line: a headline under 12 words, no full stop, no label.\n"
        "- Then 2 to 4 short paragraphs, each on its own line, under 230 words in total.\n"
        "- Explain the reason behind every notable rise or fall (about 1.5% or more on the day, or a big weekly swing), biggest first.\n"
        "- Base reasons on the headlines. If they don't explain a move, say the cause is unclear. Never invent reasons.\n"
        "- Mention the euro impact if EUR/USD moved meaningfully.\n"
        "- Plain text only: no markdown, bullet points, headings or emojis.\n"
        "- No investment advice.\n"
        "- Final line: SOURCES: followed by the numbers of up to 4 headlines you relied on, e.g. SOURCES: 2, 5\n"
        "- Output nothing else."
    )

    text = chat(prompt)
    parts = [p.strip().strip("#*").strip() for p in text.split("\n") if p.strip()]
    picked = []
    if parts and parts[-1].upper().startswith("SOURCES"):
        for tok in parts.pop().split(":", 1)[-1].replace(",", " ").split():
            tok = tok.strip("[]")
            if tok.isdigit():
                i = int(tok) - 1
                if 0 <= i < len(refs) and refs[i] not in picked:
                    picked.append(refs[i])
    if len(parts) < 2:
        print("Summary looked wrong - keeping previous one")
        return

    out = {
        "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "headline": parts[0],
        "paragraphs": parts[1:],
        "sources": [{"title": s["title"], "url": s["url"]} for s in picked[:4]],
    }
    with open("data/summary.json", "w") as f:
        json.dump(out, f, indent=1)
    print("Summary saved:", out["headline"])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Summary failed, keeping previous one:", e)
