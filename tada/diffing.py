from datetime import datetime
from pathlib import Path

from .models import Claim, ClaimDiff, DeckDiffReport
from core.trace import Tracer
from core.llm import complete


def _word_overlap_similarity(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / max(len(words_a), len(words_b))


def _classify_claim_change(prev: Claim, curr: Claim) -> str:
    if prev.statement == curr.statement:
        return "unchanged"
    similarity = _word_overlap_similarity(prev.statement, curr.statement)
    if similarity > 0.5:
        return "changed"
    return "changed"


def diff_decks(v1_claims: list[Claim], v2_claims: list[Claim], v1_filename: str, v2_filename: str, tracer: Tracer) -> DeckDiffReport:
    tracer.step(f"diffing {Path(v1_filename).name} vs {Path(v2_filename).name}")

    claim_diffs: list[ClaimDiff] = []
    matched_v1: set[int] = set()
    matched_v2: set[int] = set()

    for i, curr in enumerate(v2_claims):
        best_match_idx = -1
        best_score = 0.0
        for j, prev in enumerate(v1_claims):
            score = _word_overlap_similarity(prev.statement, curr.statement)
            if score > best_score and score > 0.3 and j not in matched_v1:
                best_score = score
                best_match_idx = j

        if best_match_idx >= 0:
            matched_v1.add(best_match_idx)
            matched_v2.add(i)
            status = _classify_claim_change(v1_claims[best_match_idx], curr)
            claim_diffs.append(ClaimDiff(
                status=status,
                claim_id=curr.id,
                statement=curr.statement,
                category=curr.category,
                source_slide=curr.source_slide,
                previous_statement=v1_claims[best_match_idx].statement if status == "changed" else None,
            ))
        else:
            claim_diffs.append(ClaimDiff(
                status="added",
                claim_id=curr.id,
                statement=curr.statement,
                category=curr.category,
                source_slide=curr.source_slide,
            ))

    for j, prev in enumerate(v1_claims):
        if j not in matched_v1:
            claim_diffs.append(ClaimDiff(
                status="removed",
                statement=prev.statement,
                category=prev.category,
                source_slide=prev.source_slide,
            ))

    summary = {
        "added": sum(1 for d in claim_diffs if d.status == "added"),
        "removed": sum(1 for d in claim_diffs if d.status == "removed"),
        "changed": sum(1 for d in claim_diffs if d.status == "changed"),
        "unchanged": sum(1 for d in claim_diffs if d.status == "unchanged"),
    }

    signals = []
    added_arch = [d for d in claim_diffs if d.status == "added" and d.category == "model_architecture"]
    removed_data = [d for d in claim_diffs if d.status == "removed" and d.category == "data_moat"]
    if removed_data:
        signals.append(f"Dropped data moat claim: '{removed_data[0].statement[:60]}...' — possible pivot or reduced confidence")
    if added_arch:
        signals.append(f"New architecture claim: '{added_arch[0].statement[:60]}...' — track whether this evolves")
    if summary.get("changed", 0) > 0:
        signals.append(f"{summary['changed']} claims were reworded — may indicate messaging refinement or factual correction")

    tracer.ok(f"diff complete: {summary['added']} added, {summary['removed']} removed, {summary['changed']} changed")
    return DeckDiffReport(
        v1_filename=v1_filename,
        v2_filename=v2_filename,
        generated_at=datetime.now(),
        claim_diffs=claim_diffs,
        summary=summary,
        signals=signals,
    )
