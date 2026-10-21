import json, os, datetime, statistics
from ai import chat, news

TOP_ALL_TIME = 12
RECENT_DAYS = 30
NEWS_FROM = "2024-01-01"
BATCH = 15
PATH = "data/events.json"


def daily_moves(dates, vals):
    out, prev = [], None
    for d, v in zip(dates, vals):
        if v is None:
            continue
        if prev is not None and prev != 0 and v != prev:
            out.append((d, round((v - prev) / abs(prev) * 100, 2), v))
        prev = v
    return out


def candidates(dates, vals):
    moves = daily_moves(dates, vals)
    if len(moves) < 50:
        return []
    sd = statistics.pstdev([m[1] for m in moves[-520:]])
    thresh = max(3 * sd, 2.0)
    top = sorted(moves, key=lambda m: abs(m[1]), reverse=True)[:TOP_ALL_TIME]
    cutoff = (datetime.date.today() - datetime.timedelta(days=RECENT_DAYS)).isoformat()
    recent = [m for m in moves if m[0] >= cutoff and abs(m[1]) >= thresh]
    picked = {}
    for m in top + recent:
        picked[m[0]] = m
    return sorted(picked.values())


def ask(name, unit, moves):
    rows = []
    for d, p, v in moves:
        line = "%s: %+.2f%% (closed at $%.2f per %s)" % (d, p, v, unit)
        if d >= NEWS_FROM:
            dd = datetime.date.fromisoformat(d)
            q = "%s price after:%s before:%s" % (name.lower(), (dd - datetime.timedelta(days=1)).isoformat(), (dd + datetime.timedelta(days=2)).isoformat())
            hs = news(q, 5)
            if hs:
                line += "\n  Headlines that day: " + " | ".join(h["title"] for h in hs)
        rows.append(line)
    prompt = (
        "Below are big one-day price moves in " + name + " front-month futures. For each date, explain what caused the move. "
        "Use the headlines where given, otherwise your own knowledge of well-known market events. "
        "Some moves in continuous front-month futures data come from the contract rolling over to the next month rather than news; "
        "if that is the likely cause, say so. If the cause is genuinely unclear, say so rather than guessing.\n\n"
        + "\n".join(rows) + "\n\n"
        'Reply with ONLY a JSON object, no other text, in this exact form:\n'
        '{"events": [{"date": "YYYY-MM-DD", "title": "short cause, under 8 words", "reason": "one or two plain sentences explaining why the price moved"}]}\n'
        "Include every date listed."
    )
    text = chat(prompt, 4000)
    a, z = text.find("{"), text.rfind("}")
    return json.loads(text[a:z + 1]).get("events", [])


def main():
    with open("data/latest.json") as f:
        latest = json.load(f)
    with open("data/history.json") as f:
        hist = json.load(f)
    events = []
    if os.path.exists(PATH):
        with open(PATH) as f:
            events = json.load(f)
    have = set((e["key"], e["date"]) for e in events)

    for it in latest["items"]:
        key = it["key"]
        cands = candidates(hist["dates"], hist["series"][key])
        missing = [m for m in cands if (key, m[0]) not in have]
        for i in range(0, len(missing), BATCH):
            chunk = missing[i:i + BATCH]
            try:
                answers = ask(it["name"], it["unit"], chunk)
            except Exception as e:
                print("Failed for", it["name"], e)
                continue
            by_date = dict((m[0], m) for m in chunk)
            for a in answers:
                m = by_date.get(a.get("date"))
                if not m or (key, m[0]) in have:
                    continue
                events.append({"key": key, "date": m[0], "change_pct": m[1],
                               "title": a.get("title", ""), "reason": a.get("reason", "")})
                have.add((key, m[0]))
            events.sort(key=lambda e: (e["key"], e["date"]))
            with open(PATH, "w") as f:
                json.dump(events, f, indent=1)
            print(it["name"], "- added", len(answers), "events")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Events failed, keeping previous:", e)
