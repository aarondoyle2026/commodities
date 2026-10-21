import os, html, urllib.parse
import xml.etree.ElementTree as ET
import requests

TOKEN = os.environ.get("GITHUB_TOKEN")
URL = "https://models.github.ai/inference/chat/completions"
MODELS = ["openai/gpt-4.1", "openai/gpt-4.1-mini", "openai/gpt-4o", "openai/gpt-4o-mini", "meta/llama-3.3-70b-instruct"]


def chat(prompt, max_tokens=1500):
    if not TOKEN:
        raise RuntimeError("No GITHUB_TOKEN available")
    headers = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}
    last = None
    for model in MODELS:
        try:
            r = requests.post(URL, headers=headers, timeout=180, json={
                "model": model, "max_tokens": max_tokens, "temperature": 0.3,
                "messages": [{"role": "user", "content": prompt}]})
            if r.status_code != 200:
                last = "%s: %s %s" % (model, r.status_code, r.text[:200])
                print("Model failed -", last)
                continue
            print("Used model", model)
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last = "%s: %s" % (model, e)
            print("Model failed -", last)
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
