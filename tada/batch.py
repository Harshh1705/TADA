from datetime import datetime
from pathlib import Path
from .models import PortfolioEntry, PortfolioMap, Verdict
from core.trace import Tracer
from core.llm import complete


def _infer_company_name_from_filename(deck_filename: str) -> str:
    stem = Path(deck_filename).stem
    for prefix in ["deck-", "pitch-", "pitch_deck-", "series-a-", "seed-"]:
        if stem.lower().startswith(prefix):
            stem = stem[len(prefix):]
    return stem.replace("-", " ").replace("_", " ").strip().title()


def build_portfolio_map(entries: list[tuple[str, list[Verdict]]], tracer: Tracer) -> PortfolioMap:
    tracer.step(f"building portfolio map from {len(entries)} decks")

    portfolio_entries: list[PortfolioEntry] = []
    all_categories: dict[str, int] = {}
    all_contradicted: list[str] = []

    for deck_path, verdicts in entries:
        company = _infer_company_name_from_filename(deck_path)
        cat_counts: dict[str, int] = {}
        verdict_counts: dict[str, int] = {"supported": 0, "contradicted": 0, "inconclusive": 0}
        risks: list[str] = []

        for v in verdicts:
            cat = v.claim.category
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            all_categories[cat] = all_categories.get(cat, 0) + 1
            verdict_counts[v.verdict] = verdict_counts.get(v.verdict, 0) + 1
            if v.verdict == "contradicted":
                risks.append(f"{v.claim.category}: {v.claim.statement[:80]}")

        portfolio_entries.append(PortfolioEntry(
            deck_filename=Path(deck_path).name,
            company_name=company,
            claim_count=len(verdicts),
            claims_by_category=cat_counts,
            verdict_summary=verdict_counts,
            key_risks=risks,
        ))
        all_contradicted.extend(risks)

    patterns = _detect_patterns(portfolio_entries)
    concentration_risks = _detect_concentration_risks(portfolio_entries)

    tracer.ok(f"portfolio map complete: {len(portfolio_entries)} companies, {len(patterns)} patterns")
    return PortfolioMap(
        generated_at=datetime.now(),
        entries=portfolio_entries,
        cross_portfolio_patterns=patterns,
        concentration_risks=concentration_risks,
    )


def _detect_patterns(entries: list[PortfolioEntry]) -> list[str]:
    if not entries:
        return []

    cat_dists: dict[str, int] = {}
    for e in entries:
        for cat, count in e.claims_by_category.items():
            cat_dists[cat] = cat_dists.get(cat, 0) + count

    patterns = []
    for cat, count in sorted(cat_dists.items(), key=lambda x: -x[1]):
        pct = count / sum(cat_dists.values()) * 100
        patterns.append(f"{pct:.0f}% of all claims are about {cat.replace('_', ' ')} ({count} total)")

    contradicted_count = sum(1 for e in entries if e.verdict_summary.get("contradicted", 0) > 0)
    if contradicted_count > 0:
        patterns.append(f"{contradicted_count}/{len(entries)} companies have contradicted claims requiring follow-up")

    return patterns


def _detect_concentration_risks(entries: list[PortfolioEntry]) -> list[str]:
    risks = []
    model_arch_count = sum(1 for e in entries if e.claims_by_category.get("model_architecture", 0) > 0)
    data_moat_count = sum(1 for e in entries if e.claims_by_category.get("data_moat", 0) > 0)

    if model_arch_count > len(entries) * 0.5:
        risks.append(f"{model_arch_count}/{len(entries)} companies claim model architecture advantages — verify they aren't all fine-tuning the same base model")

    if data_moat_count > len(entries) * 0.5:
        risks.append(f"{data_moat_count}/{len(entries)} companies claim proprietary data moats — cross-check for overlapping data sources")

    return risks


def synthesize_portfolio_summary(map: PortfolioMap) -> str:
    lines = [
        f"# Portfolio Map — {map.generated_at.strftime('%Y-%m-%d')}",
        f"**Companies analyzed:** {len(map.entries)}",
        "",
        "## Cross-Portfolio Patterns",
        "",
    ]
    for p in map.cross_portfolio_patterns:
        lines.append(f"- {p}")

    lines.extend(["", "## Concentration Risks", ""])
    for r in map.concentration_risks:
        lines.append(f"- ⚠️ {r}")

    lines.extend(["", "## Per-Company Summary", ""])
    lines.append("| Company | Claims | Model Arch | Data Moat | Tech Diff | Other | ✅ | ❌ | ⚠️ | Risks |")
    lines.append("|---------|--------|-----------|----------|----------|-------|----|----|----|-------|")
    for e in map.entries:
        lines.append(
            f"| {e.company_name} | {e.claim_count} | "
            f"{e.claims_by_category.get('model_architecture', 0)} | "
            f"{e.claims_by_category.get('data_moat', 0)} | "
            f"{e.claims_by_category.get('technical_differentiation', 0)} | "
            f"{e.claims_by_category.get('other', 0)} | "
            f"{e.verdict_summary.get('supported', 0)} | "
            f"{e.verdict_summary.get('contradicted', 0)} | "
            f"{e.verdict_summary.get('inconclusive', 0)} | "
            f"{'; '.join(e.key_risks[:2])} "
        )

    return "\n".join(lines)
