import json

from .models import Claim, Evidence, Verdict
from core.llm import complete
from core.trace import Tracer


_SYSTEM_PROMPT = (
    "You are a technical AI diligence analyst. Given a claim from a pitch deck "
    "and evidence gathered from public sources, produce a verdict.\n\n"
    "- supported: the evidence clearly supports the claim\n"
    "- contradicted: the evidence clearly contradicts the claim\n"
    "- inconclusive: the evidence is insufficient, ambiguous, or not found\n\n"
    "Return a JSON object with:\n"
    "  verdict: 'supported' | 'contradicted' | 'inconclusive'\n"
    "  reasoning: one paragraph explaining the verdict with specific reference to the evidence\n"
    "  evidence_judgments: list of objects with 'text' (matching evidence text), "
    "'source_url' (matching evidence URL), 'supports' (true/false/null)\n\n"
    "Return ONLY valid JSON. No markdown, no explanation."
)


def judge(claim: Claim, evidence: list[Evidence], tracer: Tracer) -> Verdict:
    tracer.debug(f"judging claim [{claim.id}]: {claim.statement[:60]}...")

    if not evidence:
        tracer.debug(f"verdict: INCONCLUSIVE — no evidence found")
        return Verdict(
            claim=claim,
            evidence=[],
            verdict="inconclusive",
            reasoning="No publicly available evidence was found to support or contradict this claim.",
        )

    prompt_parts = [
        f"Claim (category: {claim.category}):\n{claim.statement}\n",
        "Evidence:",
    ]
    for i, ev in enumerate(evidence, 1):
        prompt_parts.append(f"\n[{i}] URL: {ev.source_url}\n{ev.text[:800]}")

    prompt = "\n".join(prompt_parts)

    raw = complete(prompt, system=_SYSTEM_PROMPT)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        tracer.debug("  JSON parse failed, returning inconclusive")
        return Verdict(
            claim=claim,
            evidence=evidence,
            verdict="inconclusive",
            reasoning="Failed to parse LLM judgment output.",
        )

    judged_evidence = []
    for ej in data.get("evidence_judgments", []):
        judged_evidence.append(
            Evidence(
                text=ej.get("text", ""),
                source_url=ej.get("source_url", ""),
                supports=ej.get("supports"),
            )
        )

    v = data.get("verdict", "inconclusive")
    if v not in ("supported", "contradicted", "inconclusive"):
        v = "inconclusive"

    tracer.debug(f"verdict: {v.upper()}")
    return Verdict(
        claim=claim,
        evidence=judged_evidence or evidence,
        verdict=v,
        reasoning=data.get("reasoning", "No reasoning provided."),
    )
