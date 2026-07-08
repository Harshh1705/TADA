from .models import (
    DiligenceReport, Verdict, DataMoatForensic,
    InfrastructureReport, TalentReport, FolioPyCrossRef,
)


_VERDICT_EMOJI = {
    "supported": "✅ Supported",
    "contradicted": "❌ Contradicted",
    "inconclusive": "⚠️ Inconclusive",
}


def render(report: DiligenceReport) -> str:
    lines: list[str] = []

    lines.append(f"# Diligence Report: {report.deck_filename}")
    lines.append(f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Claims analyzed:** {len(report.verdicts)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, v in enumerate(report.verdicts, 1):
        lines.append(f"## Claim {i}: {v.claim.statement}")
        lines.append("")
        lines.append(f"- **Category:** `{v.claim.category}`")
        lines.append(f"- **Source Slide:** Page {v.claim.source_slide}")
        lines.append(f"- **Verdict:** **{_VERDICT_EMOJI.get(v.verdict, v.verdict)}**")
        lines.append("")
        lines.append("### Reasoning")
        lines.append("")
        lines.append(v.reasoning)
        lines.append("")

        if v.evidence:
            lines.append("### Evidence")
            lines.append("")
            for j, ev in enumerate(v.evidence, 1):
                support_label = {
                    True: "Supports claim",
                    False: "Contradicts claim",
                    None: "Inconclusive",
                }.get(ev.supports, "Inconclusive")
                lines.append(f"{j}. **{support_label}**")
                lines.append(f"   - Source: {ev.source_url}")
                lines.append(f"   - Excerpt: {ev.text[:300]}...")
                lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("")
    summary_supported = sum(1 for v in report.verdicts if v.verdict == "supported")
    summary_contradicted = sum(1 for v in report.verdicts if v.verdict == "contradicted")
    summary_inconclusive = sum(1 for v in report.verdicts if v.verdict == "inconclusive")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Verdict | Count |")
    lines.append(f"|---------|-------|")
    lines.append(f"| ✅ Supported | {summary_supported} |")
    lines.append(f"| ❌ Contradicted | {summary_contradicted} |")
    lines.append(f"| ⚠️ Inconclusive | {summary_inconclusive} |")

    return "\n".join(lines)


def render_data_moat(forensic: DataMoatForensic) -> str:
    lines = [
        "---",
        "",
        "## Data Moat Forensics",
        "",
        f"**Claimed data source:** {forensic.claimed_data_source}",
        "",
        "### Similar Public Datasets",
        "",
    ]

    if forensic.similar_public_datasets:
        lines.append("| Dataset | Source | URL |")
        lines.append("|---------|--------|-----|")
        for d in forensic.similar_public_datasets[:8]:
            lines.append(f"| {d.name} | {d.source} | {d.url} |")
    else:
        lines.append("No similar public datasets found via automated search.")
    lines.append("")

    if forensic.fine_tune_comparisons:
        lines.append("### Open-Source Fine-Tune Comparisons")
        lines.append("")
        for c in forensic.fine_tune_comparisons[:4]:
            lines.append(f"- [{c.paper_title}]({c.paper_url}) — {c.relevance[:200]}")
        lines.append("")

    lines.append("### Strategic Verdict")
    lines.append("")
    lines.append(f"{forensic.verdict}")
    lines.append("")

    lines.append("### Partner Suggestion")
    lines.append("")
    lines.append(f"> {forensic.suggestion}")
    lines.append("")

    return "\n".join(lines)


def render_infrastructure(report: InfrastructureReport) -> str:
    lines = [
        "---",
        "",
        "## Infrastructure Flight Check",
        "",
        f"**Company:** {report.company_name}",
        "",
        "### Training Infrastructure",
        "",
    ]

    if report.training_infra:
        for f in report.training_infra:
            lines.append(f"- {f.detail} ({f.source_url})" if f.source_url else f"- {f.detail}")
    else:
        lines.append("No training infrastructure signals detected from public sources.")
    lines.append("")

    lines.append("### Inference Infrastructure")
    lines.append("")
    if report.inference_infra:
        for f in report.inference_infra:
            lines.append(f"- {f.detail} ({f.source_url})" if f.source_url else f"- {f.detail}")
    else:
        lines.append("No inference infrastructure signals detected from public sources.")
    lines.append("")

    if report.compliance_flags:
        lines.append("### Compliance Flags")
        lines.append("")
        for flag in report.compliance_flags:
            severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(flag.severity, "⚪")
            lines.append(f"{severity_emoji} **{flag.regulation}** ({flag.severity.upper()})")
            lines.append(f"   - {flag.detail}")
            lines.append(f"   - **Recommendation:** {flag.recommendation}")
            lines.append("")

    lines.append("### Pre-Flight Checklist")
    lines.append("")
    for i, item in enumerate(report.checklist, 1):
        lines.append(f"{i}. [ ] {item}")

    return "\n".join(lines)


def render_talent(report: TalentReport) -> str:
    lines = [
        "---",
        "",
        "## Talent Match",
        "",
        f"**Company:** {report.company_name}",
        "",
        "### Detected Tech Stack",
        "",
    ]

    if report.detected_stack:
        lines.append("| Technology | Category | Confidence |")
        lines.append("|------------|----------|------------|")
        for t in report.detected_stack:
            lines.append(f"| {t.technology} | {t.category} | {t.confidence:.0%} |")
    else:
        lines.append("No tech stack detected from public sources.")
    lines.append("")

    if report.matches:
        lines.append("### Potential Advisors / Hires")
        lines.append("")
        for m in report.matches:
            lines.append(f"#### {m.name} (Match: {m.match_score:.0%})")
            lines.append(f"- **Expertise:** {', '.join(m.expertise)}")
            lines.append(f"- **Past Companies:** {', '.join(m.past_companies)}")
            lines.append(f"- **Availability:** {m.availability}")
            lines.append(f"- **Recommendation:** {m.recommendation}")
            lines.append("")
    else:
        lines.append("No matching contacts found in network.")

    return "\n".join(lines)


def render_foliopy_crossref(ref: FolioPyCrossRef) -> str:
    lines = [
        "---",
        "",
        "## FolioPy Cross-Reference",
        "",
    ]

    if ref.company_found:
        lines.append(f"✅ **Company found in FolioPy portfolio**")
        lines.append(f"- **Name:** {ref.company_name}")
        if ref.company_url:
            lines.append(f"- **URL:** {ref.company_url}")
        if ref.last_checked:
            lines.append(f"- **Last checked:** {ref.last_checked}")
        if ref.monitoring_events:
            lines.append("")
            lines.append("### Recent Monitoring Events")
            lines.append("")
            for ev in ref.monitoring_events[:8]:
                lines.append(f"- {ev}")
        if ref.contradictions:
            lines.append("")
            lines.append("### ⚠️ Deck vs. Public Monitoring Contradictions")
            lines.append("")
            for c in ref.contradictions:
                lines.append(f"- {c}")
    else:
        lines.append("ℹ️ **Company not found in FolioPy portfolio.**")
        lines.append("")
        lines.append("Either this company is not being tracked yet, or FolioPy's Supabase is not configured.")
        lines.append("Run `FolioPy add <name> --url <url>` to start tracking this company.")

    return "\n".join(lines)
