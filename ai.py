import os, time, html, urllib.parse
import xml.etree.ElementTree as ET
import requests

KEY = os.environ.get("GEMINI_API_KEY")
MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
BASE = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"


def chat(prompt, max_tokens=1500):
    if not KEY:
        raise RuntimeError("No GEMINI_API_KEY set")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": max(max_tokens, 1500) * 4},
    }
    last = None
    for model in MODELS:
        for attempt in range(3):
            try:
                r = requests.post(BASE % model, params={"key": KEY}, json=body, timeout=180)
            except Exception as e:
                last = "%s: %s" % (model, e)
                print("Request error -", last)
                break
            if r.status_code == 429:
                print("Rate limited on", model, "- waiting 40s")
                time.sleep(40)
                continue
            try:
                data = r.json()
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                if not text:
                    raise ValueError("empty reply")
                print("Used model", model)
                time.sleep(5)
                return text
            except Exception:
                last = "%s: status %s, body: %s" % (model, r.status_code, (r.text or "(empty)")[:300].replace("\n", " "))
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
