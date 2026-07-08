import hashlib
import time
import warnings
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
import trafilatura

warnings.filterwarnings("ignore", message="This package.*duckduckgo_search.*", category=RuntimeWarning)
from duckduckgo_search import DDGS

from .config import load_config
from .trace import Tracer


@dataclass
class SourceChunk:
    url: str
    text: str
    source_type: str
    title: str = ""
    published_date: str = ""
    snippet: str = ""
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "published_date": self.published_date,
            "snippet": self.snippet,
            "source_type": self.source_type,
            "text": self.text[:2000],
            "word_count": self.word_count,
        }


_visited_domains: dict[str, float] = {}


def _rate_limit(domain: str):
    now = time.time()
    if domain in _visited_domains:
        elapsed = now - _visited_domains[domain]
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)
    _visited_domains[domain] = time.time()


def fetch_url(url: str, tracer: Tracer) -> tuple[str | None, str]:
    try:
        domain = urlparse(url).netloc
        _rate_limit(domain)
        resp = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Tada/1.0; diligence-bot)"
            },
        )
        resp.raise_for_status()
        text = trafilatura.extract(resp.text)
        if not text:
            text = resp.text[:10000]
        return text, ""
    except Exception as e:
        tracer.debug(f"  fetch failed: {url}", error=str(e))
        return None, ""


def search_tavily(query: str, api_key: str, max_results: int = 5) -> list[dict]:
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": max_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": r["title"],
                "url": r["url"],
                "snippet": r["content"],
                "published_date": r.get("published_date", ""),
            }
            for r in data.get("results", [])
        ]
    except Exception:
        return []


def search_web(query: str, max_results: int = 5) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r["title"],
                    "url": r["href"],
                    "snippet": r["body"],
                    "published_date": "",
                }
                for r in results
            ]
    except Exception:
        return []


def research_company(name: str, url: str, tracer: Tracer) -> list[SourceChunk]:
    chunks: list[SourceChunk] = []
    content_hashes: set[str] = set()

    tracer.step(f"fetching primary: {url}")
    paths = ["", "/blog", "/news", "/careers", "/jobs", "/press"]

    for path in paths:
        full_url = url.rstrip("/") + path
        text, date = fetch_url(full_url, tracer)
        if text:
            h = hashlib.md5(text.encode()).hexdigest()
            if h not in content_hashes:
                content_hashes.add(h)
                chunks.append(
                    SourceChunk(
                        url=full_url,
                        text=text,
                        source_type="primary",
                        published_date=date,
                    )
                )
                tracer.debug(f"  {full_url}: {len(text.split())} words" + (f" [{date}]" if date else ""))
        else:
            tracer.debug(f"  {full_url}: skipped")

    cfg = load_config()
    queries = [
        f'"{name}" funding',
        f'"{name}" hiring OR launch',
        f'"{name}" news',
    ]

    for query in queries:
        tavily_count = 0
        if cfg.tavily_api_key:
            results = search_tavily(query, cfg.tavily_api_key, max_results=5)
            for r in results:
                text, date = fetch_url(r["url"], tracer)
                if text:
                    h = hashlib.md5(text.encode()).hexdigest()
                    if h not in content_hashes:
                        content_hashes.add(h)
                        chunks.append(
                            SourceChunk(
                                url=r["url"],
                                text=text,
                                source_type="secondary",
                                title=r.get("title", ""),
                                published_date=r.get("published_date", "") or date,
                                snippet=r.get("snippet", ""),
                            )
                        )
                        tavily_count += 1
                        published = r.get("published_date", "") or date
                        tracer.debug(
                            f"  tavily: {r['url']} ({len(text.split())} words)"
                            + (f" [{published}]" if published else "")
                        )

        ddg_count = 0
        results = search_web(query, max_results=3)
        for r in results:
            text, date = fetch_url(r["url"], tracer)
            if text:
                h = hashlib.md5(text.encode()).hexdigest()
                if h not in content_hashes:
                    content_hashes.add(h)
                    chunks.append(
                        SourceChunk(
                            url=r["url"],
                            text=text,
                            source_type="secondary",
                            title=r.get("title", ""),
                            published_date=r.get("published_date", "") or date,
                            snippet=r.get("snippet", ""),
                        )
                    )
                    ddg_count += 1
                    tracer.debug(
                        f"  ddg: {r['url']} ({len(text.split())} words)"
                    )

        tracer.debug(f"  query '{query}': {tavily_count + ddg_count} sources (tavily={tavily_count}, ddg={ddg_count})")

    tracer.ok(f"research complete: {len(chunks)} sources collected")
    return chunks
