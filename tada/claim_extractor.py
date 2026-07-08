import json

from .models import Claim
from core.llm import complete
from core.trace import Tracer


_SYSTEM_PROMPT = (
    "You are a technical AI diligence analyst. Extract technical AI claims from a pitch deck.\n\n"
    "Categories:\n"
    "- model_architecture: claims about model design (fine-tune vs foundation vs from-scratch, architecture type, training approach)\n"
    "- data_moat: claims about proprietary data, data advantages, exclusive access\n"
    "- technical_differentiation: claims about what's technically novel or uniquely capable\n"
    "- other: any other technical AI claim not covered above\n\n"
    "Return a JSON array of objects with:\n"
    "  id: short unique string (e.g. 'c1', 'c2')\n"
    "  category: one of the four above\n"
    "  statement: the claim as stated, paraphrased concisely\n"
    "  source_slide: the page number where it appeared\n\n"
    "Return ONLY valid JSON. No markdown, no explanation."
)


def extract_claims(pages: list[tuple[int, str]], tracer: Tracer) -> list[Claim]:
    tracer.step("extracting technical claims from deck text")

    deck_text = "\n\n".join(
        f"[Page {num}]\n{text[:2000]}" for num, text in pages
    )

    raw = complete(deck_text, system=_SYSTEM_PROMPT)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        tracer.step("  JSON parse failed, retrying with stricter instruction")
        raw = complete(
            deck_text + "\n\nIMPORTANT: Return ONLY a valid JSON array. No markdown, no code fences.",
            system=_SYSTEM_PROMPT,
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            tracer.step("  claim extraction failed after retry — returning empty")
            return []

    if not isinstance(data, list):
        data = [data]

    claims = []
    for item in data:
        try:
            claims.append(Claim(**item))
        except Exception:
            continue

    tracer.ok(
        f"extracted {len(claims)} claims "
        f"({', '.join(f'{c.category}' for c in claims)})"
    )
    return claims
