from .models import Claim, Evidence
from core.trace import Tracer
from core.research import search_tavily, search_web, fetch_url
from core.config import load_config


_QUERY_TEMPLATES = {
    "model_architecture": [
        '"{company}" model architecture OR paper OR technical blog',
        '"{company}" foundation model OR training OR architecture',
    ],
    "data_moat": [
        '"{company}" data OR dataset OR proprietary data',
        '"{company}" training data OR data partnership',
    ],
    "technical_differentiation": [
        '"{company}" technology OR innovation OR novel',
        '"{company}" benchmark OR performance OR capability',
    ],
    "other": [
        '"{company}" AI OR technology',
    ],
}


def _infer_company_name(claim: Claim) -> str:
    words = claim.statement.split()[:5]
    return " ".join(words)


def ground_claim(claim: Claim, tracer: Tracer, company_name: str | None = None) -> list[Evidence]:
    evidence_list: list[Evidence] = []
    seen_urls: set[str] = set()
    company = company_name or _infer_company_name(claim)

    templates = _QUERY_TEMPLATES.get(claim.category, _QUERY_TEMPLATES["other"])

    cfg = load_config()
    has_tavily = bool(cfg.tavily_api_key)

    for template in templates:
        query = template.format(company=company)
        tracer.debug(f"  searching: {query}")

        if has_tavily:
            results = search_tavily(query, cfg.tavily_api_key, max_results=3)
        else:
            results = search_web(query, max_results=3)

        for r in results:
            url = r["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            text, _ = fetch_url(url, tracer)
            if text:
                snippet = text[:500]
                evidence_list.append(
                    Evidence(
                        text=snippet,
                        source_url=url,
                    )
                )
                tracer.debug(f"  evidence from: {url} ({len(text.split())} words)")

        if len(evidence_list) >= 3:
            break

    tracer.debug(f"grounding complete: {len(evidence_list)} evidence items")
    return evidence_list
