import os, time, html, urllib.parse
import xml.etree.ElementTree as ET
import requests

KEY = os.environ.get("GEMINI_API_KEY")
ATTEMPTS = [
    ("gemini-3.8-flash", True),
    ("gemini-3.8-flash", False),
    ("gemini-3.5-flash-lite", True),
    ("gemini-3.5-flash-lite", False),
]
BASE = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"


def chat(prompt, max_tokens=1500):
    if not KEY:
        raise RuntimeError("No GEMINI_API_KEY set")
    last = None
    for model, search in ATTEMPTS:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": max(max_tokens, 1500) * 4},
        }
        if search:
            body["tools"] = [{"google_search": {}}]
        label = model + (" + search" if search else "")
        for attempt in range(2):
            try:
                r = requests.post(BASE % model, params={"key": KEY}, json=body, timeout=180)
            except Exception as e:
                last = "%s: %s" % (label, e)
                print("Request error -", last)
                break
            if r.status_code == 429 and attempt == 0:
                print("Rate limited on", label, "- waiting 40s")
                time.sleep(40)
                continue
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                if not text:
                    raise ValueError("empty reply")
                print("Used model", label)
                time.sleep(5)
                return text
            except Exception:
                last = "%s: status %s, body: %s" % (label, r.status_code, (r.text or "(empty)")[:300].replace("\n", " "))
                print("Model failed -", last)
                break
    raise RuntimeError("All models failed. Last error: %s" % last)


def news(query, limit=6):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-IE&gl=IE&ceid=IE:en"
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
    except Exception as e:
        print("News fetch failed for", query, e)
        return []
    out = []
    for it in root.iter("item"):
        out.append({"title": html.unescape(it.findtext("title") or ""), "url": it.findtext("link") or ""})
        if len(out) >= limit:
            break
    return out
