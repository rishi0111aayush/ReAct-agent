"""
tools/web.py — Web tools: web_search, wikipedia_search, get_weather.
"""
import requests
from bs4 import BeautifulSoup

from app.cache import cache


def web_search(query: str) -> str:
    """Search DuckDuckGo and return top results as plain text (Redis-cached 1 h)."""
    cached = cache.get_search(query)
    if cached is not None:
        return cached
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url     = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp    = requests.get(url, headers=headers, timeout=8)
        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result__body")[:4]:
            title   = r.select_one(".result__title")
            snippet = r.select_one(".result__snippet")
            if title and snippet:
                results.append(f"- {title.get_text(strip=True)}: {snippet.get_text(strip=True)}")
        result = "\n".join(results) if results else "No results found."
        cache.set_search(query, result)
        return result
    except Exception as e:
        return f"Search error: {e}"


def wikipedia_search(query: str) -> str:
    """Fetch a concise Wikipedia summary for a topic."""
    try:
        url  = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(query)
        resp = requests.get(url, headers={"User-Agent": "Boozo.ai/1.0"}, timeout=8)
        if resp.status_code == 404:
            return f"No Wikipedia article found for '{query}'."
        resp.raise_for_status()
        data    = resp.json()
        title   = data.get("title", query)
        extract = data.get("extract", "No summary available.")
        return f"**{title}**\n\n{extract}"
    except Exception as e:
        return f"Wikipedia error: {e}"


def get_weather(city: str) -> str:
    """Get current weather for a city using wttr.in (no API key needed)."""
    try:
        url  = f"https://wttr.in/{requests.utils.quote(city)}?format=4"
        resp = requests.get(url, headers={"User-Agent": "Boozo.ai/1.0"}, timeout=8)
        resp.raise_for_status()
        return resp.text.strip() or f"No weather data for '{city}'."
    except Exception as e:
        return f"Weather error: {e}"
