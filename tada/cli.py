import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

warnings.filterwarnings("ignore", message="This package.*duckduckgo_search.*", category=RuntimeWarning)

from .models import DiligenceReport
from .deck_parser import parse_deck
from .claim_extractor import extract_claims
from .grounding import ground_claim
from .verdict import judge
from .report import render, render_data_moat, render_infrastructure, render_talent, render_foliopy_crossref
from .dataset_forensics import analyze_data_moat
from .infrastructure import analyze_infrastructure
from .talent import analyze_talent
from .foliopy_bridge import cross_reference_with_foliopy
from .batch import build_portfolio_map, synthesize_portfolio_summary
from .diffing import diff_decks
from core.config import show_config, write_config
from core.splash import show_splash
from core.trace import Tracer

app = typer.Typer()
config_app = typer.Typer()
app.add_typer(config_app, name="config", help="Configure tada credentials.")


@config_app.command()
def set(
    provider: Optional[str] = typer.Option(None, "--provider"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    model: Optional[str] = typer.Option(None, "--model"),
    tavily_api_key: Optional[str] = typer.Option(None, "--tavily-api-key"),
):
    """Set configuration values."""
    write_config(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_model=model,
        tavily_api_key=tavily_api_key,
    )
    typer.echo("Config updated.")


@config_app.command()
def show():
    """Show current config with secrets masked."""
    cfg = show_config()
    for k, v in cfg.items():
        typer.echo(f"{k}={v}")


def _company_name_from_filename(deck_path: Path) -> str:
    return deck_path.stem.replace("_", " ").replace("-", " ").strip().title()


def _process_single_deck(deck_path: Path, tracer: Tracer, company_name: str | None = None) -> tuple[list, list]:
    pages = parse_deck(str(deck_path))
    tracer.ok(f"parsed {len(pages)} pages")

    claims = extract_claims(pages, tracer)
    if not claims:
        typer.echo("No technical AI claims found in deck.")
        raise typer.Exit(1)

    company = company_name or _company_name_from_filename(deck_path)
    verdicts = []
    for claim in claims:
        tracer.debug(f"claim [{claim.id}] ({claim.category}): {claim.statement[:80]}...")
        evidence = ground_claim(claim, tracer, company_name=company)
        verdict = judge(claim, evidence, tracer)
        verdicts.append(verdict)

    return claims, verdicts


@app.command()
def run(
    deck: str = typer.Argument(..., help="Path to pitch deck PDF"),
    repo: Optional[str] = typer.Option(None, "--repo", help="GitHub repo or docs URL for additional grounding"),
    data_moat: bool = typer.Option(False, "--data-moat", help="Run data moat forensics"),
    infra: bool = typer.Option(False, "--infra", help="Run infrastructure flight check"),
    talent: bool = typer.Option(False, "--talent", help="Run talent match analysis"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Analyze a pitch deck and produce a diligence report."""
    tracer = Tracer(verbose=verbose)
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    deck_path = Path(deck)
    if not deck_path.exists():
        typer.echo(f"Error: file not found: {deck}", err=True)
        raise typer.Exit(1)

    _run_impl(deck, repo, data_moat, infra, talent, verbose, "diligence")


@app.command()
def audit(
    deck: str = typer.Argument(..., help="Path to pitch deck PDF"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run full diligence with all modules (data moat, infra, talent, FolioPy cross-ref)."""
    _run_impl(deck, None, True, True, True, verbose, "audit")


def _run_impl(deck: str, repo: str | None, data_moat: bool, infra: bool, talent: bool, verbose: bool, command: str):
    tracer = Tracer(verbose=verbose)
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    deck_path = Path(deck)
    if not deck_path.exists():
        typer.echo(f"Error: file not found: {deck}", err=True)
        raise typer.Exit(1)

    company = _company_name_from_filename(deck_path)
    tracer.step(f"analyzing deck: {deck_path.name}")

    claims, verdicts = _process_single_deck(deck_path, tracer, company_name=company)

    extra_sections = []

    folio_ref = cross_reference_with_foliopy(company, tracer)
    extra_sections.append(render_foliopy_crossref(folio_ref))

    if data_moat:
        for v in verdicts:
            if v.claim.category == "data_moat":
                forensic = analyze_data_moat(v.claim, tracer)
                extra_sections.append(render_data_moat(forensic))

    if infra:
        infra_report = analyze_infrastructure(company, tracer)
        extra_sections.append(render_infrastructure(infra_report))

    if talent:
        talent_report = analyze_talent(company, tracer)
        extra_sections.append(render_talent(talent_report))

    report_obj = DiligenceReport(
        deck_filename=deck_path.name,
        generated_at=datetime.now(),
        verdicts=verdicts,
    )
    markdown_parts = [render(report_obj)]
    markdown_parts.extend(extra_sections)
    markdown = "\n\n".join(markdown_parts)

    safe_name = deck_path.stem.lower().replace(" ", "-")
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = reports_dir / f"{safe_name}-{command}-{date_str}.md"
    report_path.write_text(markdown, encoding="utf-8")
    tracer.ok(f"report written to {report_path}")

    supported = sum(1 for v in verdicts if v.verdict == "supported")
    contradicted = sum(1 for v in verdicts if v.verdict == "contradicted")
    inconclusive = sum(1 for v in verdicts if v.verdict == "inconclusive")
    typer.echo("")
    typer.echo("=" * 50)
    typer.echo("DILIGENCE SUMMARY")
    typer.echo("=" * 50)
    typer.echo(f"Total claims: {len(verdicts)}")
    typer.echo(f"  ✅ Supported:      {supported}")
    typer.echo(f"  ❌ Contradicted:   {contradicted}")
    typer.echo(f"  ⚠️ Inconclusive:   {inconclusive}")
    if folio_ref.company_found:
        typer.echo(f"  🔗 FolioPy:        Company tracked — {len(folio_ref.monitoring_events)} monitoring events found")
    typer.echo(f"Report: {report_path}")


@app.command()
def batch(
    decks_dir: str = typer.Argument(..., help="Directory of pitch deck PDFs"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Analyze multiple decks and produce a cross-portfolio map."""
    tracer = Tracer(verbose=verbose)
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    dir_path = Path(decks_dir)
    if not dir_path.is_dir():
        typer.echo(f"Error: not a directory: {decks_dir}", err=True)
        raise typer.Exit(1)

    pdfs = sorted(dir_path.glob("*.pdf"))
    if not pdfs:
        typer.echo(f"No PDFs found in {decks_dir}")
        raise typer.Exit(1)

    tracer.step(f"batch processing {len(pdfs)} decks from {decks_dir}")

    entries: list[tuple[str, list]] = []
    for pdf_path in pdfs:
        tracer.debug(f"--- processing: {pdf_path.name} ---")
        try:
            pages = parse_deck(str(pdf_path))
            company = _company_name_from_filename(pdf_path)
            claims = extract_claims(pages, tracer)
            if not claims:
                tracer.debug(f"  no claims found, skipping")
                continue
            verdicts = []
            for claim in claims:
                evidence = ground_claim(claim, tracer, company_name=company)
                verdict = judge(claim, evidence, tracer)
                verdicts.append(verdict)
            entries.append((str(pdf_path), verdicts))
        except Exception as e:
            tracer.debug(f"  failed: {e}")

    if not entries:
        typer.echo("No decks produced analyzable claims.")
        raise typer.Exit(1)

    portfolio_map = build_portfolio_map(entries, tracer)
    markdown = synthesize_portfolio_summary(portfolio_map)

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = reports_dir / f"portfolio-map-{date_str}.md"
    report_path.write_text(markdown, encoding="utf-8")
    tracer.ok(f"portfolio map written to {report_path}")

    typer.echo("")
    typer.echo("=" * 50)
    typer.echo("PORTFOLIO MAP SUMMARY")
    typer.echo("=" * 50)
    for e in portfolio_map.entries:
        risks = " ⚠️" if any(v > 0 for v in [e.verdict_summary.get("contradicted", 0)]) else ""
        typer.echo(f"  {e.company_name:30} {e.claim_count} claims{risks}")
    typer.echo(f"\nPatterns: {len(portfolio_map.cross_portfolio_patterns)} detected")
    typer.echo(f"Report: {report_path}")


@app.command()
def diff(
    deck_v1: str = typer.Argument(..., help="First version of deck (PDF)"),
    deck_v2: str = typer.Argument(..., help="Second version of deck (PDF)"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Compare claims across two versions of the same deck."""
    tracer = Tracer(verbose=verbose)
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    v1_path = Path(deck_v1)
    v2_path = Path(deck_v2)

    for p in [v1_path, v2_path]:
        if not p.exists():
            typer.echo(f"Error: file not found: {p}", err=True)
            raise typer.Exit(1)

    tracer.step(f"diffing {v1_path.name} vs {v2_path.name}")

    pages1 = parse_deck(str(v1_path))
    pages2 = parse_deck(str(v2_path))
    claims1 = extract_claims(pages1, tracer)
    claims2 = extract_claims(pages2, tracer)

    diff_report = diff_decks(claims1, claims2, v1_path.name, v2_path.name, tracer)

    safe_name = v2_path.stem.lower().replace(" ", "-")
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = reports_dir / f"diff-{safe_name}-{date_str}.md"

    lines = [
        f"# Deck Diff: {v1_path.name} → {v2_path.name}",
        f"**Generated:** {diff_report.generated_at.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        f"| Change | Count |",
        f"|--------|-------|",
        f"| ➕ Added | {diff_report.summary.get('added', 0)} |",
        f"| ❌ Removed | {diff_report.summary.get('removed', 0)} |",
        f"| ✏️ Changed | {diff_report.summary.get('changed', 0)} |",
        f"| 🔄 Unchanged | {diff_report.summary.get('unchanged', 0)} |",
        "",
    ]

    if diff_report.signals:
        lines.append("## Signals")
        lines.append("")
        for s in diff_report.signals:
            lines.append(f"- {s}")
        lines.append("")

    lines.append("## Per-Claim Breakdown")
    lines.append("")
    for d in diff_report.claim_diffs:
        status_emoji = {
            "added": "➕ Added",
            "removed": "❌ Removed",
            "changed": "✏️ Changed",
            "unchanged": "🔄 Unchanged",
        }.get(d.status, d.status)
        lines.append(f"### {status_emoji}: {d.statement[:80]}")
        lines.append(f"- **Category:** `{d.category}`")
        lines.append(f"- **Slide:** {d.source_slide}" if d.source_slide else "")
        if d.previous_statement:
            lines.append(f"- **Was:** {d.previous_statement}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    tracer.ok(f"diff report written to {report_path}")
    typer.echo("")
    typer.echo("=" * 50)
    typer.echo("DIFF SUMMARY")
    typer.echo("=" * 50)
    typer.echo(f"  ➕ Added:      {diff_report.summary.get('added', 0)}")
    typer.echo(f"  ❌ Removed:    {diff_report.summary.get('removed', 0)}")
    typer.echo(f"  ✏️ Changed:    {diff_report.summary.get('changed', 0)}")
    typer.echo(f"  🔄 Unchanged: {diff_report.summary.get('unchanged', 0)}")
    typer.echo(f"Report: {report_path}")


def main():
    if len(sys.argv) <= 1:
        show_splash()
        raise SystemExit(0)
    app()


if __name__ == "__main__":
    main()
