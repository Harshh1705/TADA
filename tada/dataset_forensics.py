from .models import Claim, PublicDataset, FineTuneComparison, DataMoatForensic
from core.trace import Tracer
from core.llm import complete
from core.research import search_tavily, search_web


def _search_huggingface_datasets(query: str, max_results: int = 5) -> list[dict]:
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        datasets = api.list_datasets(search=query, sort="downloads", direction=-1, limit=max_results)
        results = []
        for ds in datasets:
            results.append({
                "name": ds.id,
                "url": f"https://huggingface.co/datasets/{ds.id}",
                "description": (ds.cardData or {}).get("description", "") or "",
                "downloads": getattr(ds, "downloads", 0),
            })
        return results
    except Exception:
        return []


def _find_similar_public_datasets(claimed_source: str, tracer: Tracer) -> list[PublicDataset]:
    tracer.step(f"searching public datasets for: {claimed_source}")
    datasets: list[PublicDataset] = []

    hf_results = _search_huggingface_datasets(claimed_source, max_results=5)
    for r in hf_results:
        datasets.append(PublicDataset(
            name=r["name"],
            source="HuggingFace",
            url=r["url"],
            description=r["description"][:300],
            similarity_score=0.8,
        ))
        tracer.debug(f"  hf dataset: {r['name']}")

    web_results = search_tavily(claimed_source, max_results=3) if False else []
    web_results = search_web(f'"{claimed_source}" dataset', max_results=5)
    for r in web_results:
        datasets.append(PublicDataset(
            name=r.get("title", "Unknown dataset"),
            source="Web",
            url=r["url"],
            description=r.get("snippet", "")[:300],
            similarity_score=0.5,
        ))
        tracer.debug(f"  web dataset: {r['url']}")

    return datasets


def _find_fine_tune_comparisons(claimed_source: str, tracer: Tracer) -> list[FineTuneComparison]:
    tracer.step(f"searching for fine-tunes on similar data: {claimed_source}")
    comparisons: list[FineTuneComparison] = []

    queries = [
        f'fine-tuned on "{claimed_source}" accuracy',
        f'open source fine-tune legal text accuracy',
        f'{claimed_source} fine tune benchmark',
    ]

    for query in queries:
        results = search_tavily(query, max_results=3) if False else search_web(query, max_results=3)
        for r in results:
            comparisons.append(FineTuneComparison(
                paper_title=r.get("title", "Related work"),
                paper_url=r["url"],
                dataset_used=claimed_source,
                reported_accuracy="See source",
                relevance=r.get("snippet", "")[:200],
            ))
            tracer.debug(f"  fine-tune reference: {r['url']}")
            if len(comparisons) >= 3:
                break
        if len(comparisons) >= 3:
            break

    return comparisons


def _llm_verdict(claimed_source: str, datasets: list[PublicDataset], comparisons: list[FineTuneComparison]) -> tuple[str, str]:
    prompt = (
        f"A pitch deck claims: '{claimed_source}' is proprietary/exclusive data.\n\n"
        f"Public datasets found:\n"
        + "\n".join(f"- {d.name} ({d.source}): {d.description[:200]}" for d in datasets[:5])
        + f"\n\nOpen-source fine-tune comparisons found:\n"
        + "\n".join(f"- {c.paper_title}: {c.relevance[:200]}" for c in comparisons[:3])
        + "\n\nProduce a strategic assessment in two paragraphs:\n"
        + "1. Verdict: Is this data actually proprietary or is it replicable from public sources? Be specific.\n"
        + "2. Suggestion: What actionable advice should a VC partner give the founder? "
        + "Frame it as a way to HELP the founder build a real moat, not as a red flag to kill the deal.\n"
        + "Output format:\nVERDICT: <paragraph>\nSUGGESTION: <paragraph>"
    )

    raw = complete(prompt, system="You are a VC technical diligence analyst. Be direct, specific, and constructive.")
    verdict = ""
    suggestion = ""
    for line in raw.split("\n"):
        if line.startswith("VERDICT:"):
            verdict = line.replace("VERDICT:", "").strip()
        elif line.startswith("SUGGESTION:"):
            suggestion = line.replace("SUGGESTION:", "").strip()
    return verdict or "Unable to determine.", suggestion or "Review the data claim manually."


def analyze_data_moat(claim: Claim, tracer: Tracer) -> DataMoatForensic:
    tracer.step(f"data moat forensics for claim [{claim.id}]: {claim.statement[:60]}...")

    claimed_data = claim.statement
    datasets = _find_similar_public_datasets(claimed_data, tracer)
    comparisons = _find_fine_tune_comparisons(claimed_data, tracer)
    verdict, suggestion = _llm_verdict(claimed_data, datasets, comparisons)

    result = DataMoatForensic(
        claimed_data_source=claimed_data,
        similar_public_datasets=datasets,
        fine_tune_comparisons=comparisons,
        verdict=verdict,
        suggestion=suggestion,
    )

    tracer.ok(f"data moat forensic complete: {len(datasets)} datasets, {len(comparisons)} comparisons")
    return result
