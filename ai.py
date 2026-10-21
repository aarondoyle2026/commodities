import os, html, urllib.parse
import xml.etree.ElementTree as ET
import requests

TOKEN = os.environ.get("GITHUB_TOKEN")
ENDPOINTS = [
    "https://models.github.ai/inference/chat/completions",
    "https://models.inference.ai.azure.com/chat/completions",
]
MODELS = ["openai/gpt-4.1", "openai/gpt-4.1-mini", "openai/gpt-4o", "openai/gpt-4o-mini", "meta/llama-3.3-70b-instruct"]


def chat(prompt, max_tokens=1500):
    if not TOKEN:
        raise RuntimeError("No GITHUB_TOKEN available")
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    last = None
    for url in ENDPOINTS:
        for model in MODELS:
            name = model if "models.github.ai" in url else model.split("/", 1)[1]
            try:
                r = requests.post(url, headers=headers, timeout=180, allow_redirects=False, json={
                    "model": name, "max_tokens": max_tokens, "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]})
            except Exception as e:
                last = "%s %s: %s" % (url, name, e)
                print("Request error -", last)
                continue
            try:
                data = r.json()
                text = data["choices"][0]["message"]["content"].strip()
                print("Used model", name, "via", url)
                return text
            except Exception:
                last = "%s %s: status %s, type %s, location %s, body: %s" % (
                    url, name, r.status_code, r.headers.get("content-type"),
                    r.headers.get("location"), (r.text or "(empty)")[:300].replace("\n", " "))
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
