# Architecture — tada (Technical AI-Diligence Agent)

## Goal

Given a pitch deck (and optionally a repo/docs link), extract the deck's
specific technical AI claims and produce a claim-by-claim, evidence-backed
verdict — surfacing what a partner should scrutinize rather than replacing
their judgment.

## Non-goals (explicitly out of scope for the MVP)

- No business-model/market-size summarization — that's the "obvious," already
  commoditized version of a diligence tool (see ideation doc). This tool is
  scoped narrowly to *technical* AI claims only.
- No persistence of past reports in the MVP (stretch goal only, see below).
- No UI — CLI + generated markdown report only.
- No large claim taxonomy — 3-4 categories, not an open-ended list.
- No go/no-go recommendation output — verdicts are evidence, not decisions.

## CLI surface

| Command | Behavior |
|---|---|
| `tada config set --provider <groq\|openrouter> --api-key <key>` | Same `~/.FolioPy/config.env` as the monitoring tool — reused, not reimplemented. |
| `tada config show` | Prints config, secrets masked. |
| `tada run <deck.pdf>` | Full pipeline: parse → extract claims → ground → verdict → report. |
| `tada run <deck.pdf> --repo <github_url>` | Same, with the repo/docs link as an additional grounding source per claim (STRETCH — wire up after the PDF-only path is solid). |

## Data models (`tada/models.py`, pydantic)

```python
class Claim(BaseModel):
    id: str
    category: Literal["model_architecture", "data_moat", "technical_differentiation", "other"]
    statement: str          # the claim as stated in the deck, paraphrased
    source_slide: int

class Evidence(BaseModel):
    text: str                # short extracted snippet, paraphrased not quoted
    source_url: str
    supports: bool | None    # True/False/None (inconclusive) relative to the claim

class Verdict(BaseModel):
    claim: Claim
    evidence: list[Evidence]
    verdict: Literal["supported", "contradicted", "inconclusive"]
    reasoning: str            # one paragraph, why the verdict was reached

class DiligenceReport(BaseModel):
    deck_filename: str
    generated_at: datetime
    verdicts: list[Verdict]
```

Kept intentionally flatter than FolioPy's `Event`/`Snapshot` pair — there's no
diffing or time-series concern here, so there's no need for a `Snapshot`-like
wrapper. `DiligenceReport` is just the container for one run's output.

## Module responsibilities

**`core/config.py`, `core/llm.py`, `core/trace.py`, `core/research.py`** —
copied unmodified from FolioPy. Do not re-derive these; if something needs to
change, change it in FolioPy first and re-copy, so the two tools don't drift
into inconsistent behavior for what should be identical infra.

**`tada/deck_parser.py`** — `parse_deck(path: str) -> list[tuple[int, str]]`
using PyMuPDF (`fitz`). Iterates pages, extracts text blocks per page,
returns `(page_number, text)` tuples. Keep this dumb and literal — no
attempt to detect "slide sections" beyond page boundaries; that's not worth
building for the MVP.

**`tada/claim_extractor.py`** — `extract_claims(deck_text: list[tuple[int,
str]], tracer) -> list[Claim]`. One LLM call: full deck text (with page
numbers preserved inline) in, strict system prompt asking for claims in
exactly the 3-4 categories above as structured JSON, validated via pydantic
(retry once on validation failure, same pattern as FolioPy's extractor).

**`tada/grounding.py`** — `ground_claim(claim: Claim, tracer) ->
list[Evidence]`. For each claim: 1-2 targeted search queries built from the
claim's category and statement (e.g. for a `model_architecture` claim about
"proprietary foundation model," search `"<company>" model architecture OR
paper OR technical blog`), fetch top 2-3 results via `core/research.py`,
return raw evidence snippets (labeling still to be judged by `verdict.py`,
not decided here).

**`tada/verdict.py`** — `judge(claim: Claim, evidence: list[Evidence],
tracer) -> Verdict`. One LLM call per claim: given the claim and its gathered
evidence, output supported/contradicted/inconclusive plus a one-paragraph
reasoning. If no evidence was found at all, verdict defaults to
`inconclusive` with reasoning stating that explicitly — never guess a verdict
from the claim text alone with no grounding.

**`tada/report.py`** — `render(report: DiligenceReport) -> str`, markdown
written to `data/reports/<deck-name>-diligence.md`. One section per claim:
statement, category, verdict (bolded), reasoning, evidence list with source
links.

## Reasoning trace format (what appears on screen during the demo)

```
[tada] run acme-ai-deck.pdf
  → parsing deck: acme-ai-deck.pdf (14 pages)
  → extracting technical claims from deck text...
  → extracted 4 claims (2 model_architecture, 1 data_moat, 1 technical_differentiation)
  → claim 1 [model_architecture]: "proprietary foundation model trained from scratch"
      → searching: "Acme AI" foundation model architecture paper
      → fetched: acme.ai/technology (1,020 words)
      → fetched: arxiv.org/abs/... (abstract only)
      → judging claim against 2 evidence items...
      → verdict: CONTRADICTED — evidence suggests fine-tuned open-weights model, not from-scratch
  → claim 2 [data_moat]: "exclusive access to 10M proprietary healthcare records"
      → searching: "Acme AI" healthcare data partnership
      → no results found
      → verdict: INCONCLUSIVE — claim not independently verifiable from public sources
  ...
  → writing report to data/reports/acme-ai-deck-diligence.md
```

Narrate over this in the demo recording, same as FolioPy — this is the
"visible reasoning" requirement satisfied the same way across both tools.

## Error handling

- Deck fails to parse (corrupted/encrypted PDF) → fail fast with a clear
  error naming the file, don't attempt a partial run.
- Claim extraction returns malformed JSON → one retry with an added "return
  valid JSON only" instruction; if it fails twice, abort that run with a
  clear message (unlike FolioPy's batch `run`, there's only one deck per
  invocation, so there's no "continue to the next item" fallback here).
- No search/fetch results for a claim → verdict defaults to `inconclusive`,
  never silently omitted from the report.
- Missing/invalid config → clear error naming exactly which `tada config
  set` flag is missing.

## Stretch goals (only after the MVP above runs end-to-end on a real deck)

**1. `--repo <github_url>` grounding.** Fetch repo README + a sample of file
names/structure as an additional evidence source per relevant claim
(particularly useful for `model_architecture` and `technical_differentiation`
claims). Wire this in as one more `Evidence`-producing step in
`grounding.py`, not a separate pipeline.

**2. Supabase persistence.** If time allows: a `diligence_reports` table
(`id, deck_filename, generated_at, report_json`) so future runs could check
"have we seen a claim pattern like this before" — mirrors the knowledge-base
tool's territory conceptually, but not required for this submission.

```sql
create table diligence_reports (
    id bigint generated always as identity primary key,
    deck_filename text not null,
    generated_at timestamptz not null default now(),
    report jsonb not null
);
alter table diligence_reports disable row level security;
```

**3. `core/splash.py` logo swap.** Purely cosmetic — do this last, if at all.

## What's needed from the firm for production (writeup material)

- A small set of real portfolio/inbound decks to validate claim-extraction
  accuracy against ground truth a partner already knows.
- A decision on what "verified" should mean for claims that are inherently
  hard to check publicly (e.g. proprietary data size) — this tool can flag
  unverifiable claims, but can't manufacture certainty that doesn't exist
  publicly.
- Guidance on whether verdicts should ever be shown to founders (transparency)
  or stay strictly internal — a product/policy question, not a technical one.

## Future work (explicitly not building now)

- The two stretch items above, if not reached before submission.
- Cross-referencing verdicts against the knowledge-base tool's ingested past
  memos (e.g. "we flagged a similar architecture claim as overstated in a
  memo from 2025") — natural three-tool integration point, not built here.
- A confidence score per verdict beyond the 3-state label, if partners find
  the flat categorization too coarse in practice.
