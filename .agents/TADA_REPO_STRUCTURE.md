# Repo Structure — tada (Technical AI-Diligence Agent)

One-shot tool: a pitch deck (+ optional repo/docs link) goes in, a claim-by-claim
technical verdict comes out. No tracked-company state, no `add`/`import` — every
run is independent, unlike FolioPy's monitoring loop.

```
tada/
├── README.md                    # install + run instructions (submission requirement)
├── CONTEXT.md                   # working memory: purpose, decisions, state, build order
├── ARCHITECTURE.md              # full architecture spec
├── pyproject.toml                 # packaging + `tada` console_script entry point
├── requirements.txt
├── schema.sql                      # OPTIONAL/STRETCH — only if persisting past reports, see below
├── .gitignore
│
├── core/                             # copied from FolioPy so this tool is independently runnable
│   ├── __init__.py
│   ├── config.py                       # REUSED AS-IS — same ~/.FolioPy/config.env format
│   ├── llm.py                           # REUSED AS-IS — complete() is provider-agnostic already
│   ├── trace.py                          # REUSED AS-IS — Tracer.step()/ok()/debug()
│   ├── research.py                        # REUSED AS-IS — search()/fetch() built for FolioPy's
│   │                                         scraping pipeline; grounding claims is the same
│   │                                         "search + fetch + extract" shape as portfolio monitoring
│   └── splash.py                           # REUSED, STRETCH — swap logo text only, do last
│
├── tada/                              # this tool's own domain logic
│   ├── __init__.py
│   ├── cli.py                          # Typer app: config (delegates to core.config), run
│   ├── models.py                        # pydantic: Claim, Evidence, Verdict, DiligenceReport
│   ├── deck_parser.py                     # PyMuPDF: deck -> per-slide/section text
│   ├── claim_extractor.py                  # deck text -> list[Claim]
│   ├── grounding.py                          # Claim -> list[Evidence] via core/research.py
│   ├── verdict.py                              # Claim + Evidence -> Verdict
│   └── report.py                                # list[Verdict] -> markdown report
│
├── data/
│   └── reports/                        # one markdown report per deck, e.g. acme-ai-diligence.md
│
└── tests/
    └── test_claim_extractor.py           # the one piece worth unit testing under time pressure
```

## What's reused vs. new (this is the whole point of `core/` being shared)

| Module | Status |
|---|---|
| `core/config.py` | **Reused as-is.** Same `~/.FolioPy/config.env`. This tool only needs `LLM_PROVIDER` + `LLM_API_KEY` populated — Supabase/Tavily fields can stay empty unless you build the stretch persistence goal below. |
| `core/llm.py` | **Reused as-is.** `complete()` doesn't care what the prompt is about — a diligence verdict call is structurally the same request shape as a monitoring extraction call. |
| `core/trace.py` | **Reused as-is.** TADA needs visible reasoning per stage exactly like the monitoring tool did — same `Tracer` object, same log format, so the two demo recordings look consistent. |
| `core/research.py` | **Reused as-is.** Grounding a technical claim ("is this a fine-tune or foundation model") is search + fetch + read, same shape as researching a portfolio company. Copy it over unmodified. |
| `core/splash.py` | **Reused, cosmetic only.** Swap the logo string. Do this last, only if time remains — it's pure polish, not gradeable. |

## What's genuinely new

Only `tada/` (the package) is new work: `deck_parser.py`, `claim_extractor.py`,
`grounding.py`, `verdict.py`, `report.py`, plus a thin `cli.py`. Everything
under `core/` is a copy, not a rewrite.

## Packaging note for final submission

The assignment wants each tool independently runnable in its own subfolder. Since
`core/` is physically duplicated (not a shared installed package) between the
`pyfolio/` and `tada/` submission folders, that requirement is satisfied
automatically — each folder is self-contained. Just make sure you copy the
*final* versions of `config.py`/`llm.py`/`trace.py`/`research.py` from FolioPy
into `tada/core/` once, at the end, rather than editing two live copies in
parallel and having them drift.
