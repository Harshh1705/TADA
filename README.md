# tada — Technical AI-Diligence Agent

> **tada** reads a pitch deck (PDF), extracts its technical AI claims, grounds them against public web data, and produces an evidence-backed verdict for each claim. Optional modules verify data moats, check cross-border infrastructure compliance, and match tech stacks against your talent network.

## Why tada?

| Problem | Solution |
|---------|----------|
| "Claude with a prompt works fine for one deck" | tada scales to **20 decks at once** with `tada batch` — consistent extraction, consistent verdicts, no prompt drift |
| "I have 50 decks and can't remember what each claimed" | `tada batch` produces a **cross-portfolio matrix** showing claim category distributions and concentration risks |
| "Did the founder change their claims between v1 and v2?" | `tada diff v1.pdf v2.pdf` shows exactly what claims were **added, removed, or changed** |
| "How do I know if their 'proprietary data' is real?" | `tada run deck.pdf --data-moat` searches **HuggingFace + web** for public datasets that match their claimed data source |
| "They build on vLLM/A100s — do I know anyone who's done this before?" | `tada run deck.pdf --talent` detects their **tech stack** and matches against your **contacts network** |
| "Are they compliant with US-India cross-border regulations?" | `tada run deck.pdf --infra` checks **BIS export controls, India DPDP Act, and data residency** |
| "Claude doesn't know what I already know about this company" | tada cross-references against **FolioPy's monitoring data** — if you're already tracking this company, it surfaces contradictions between their deck and their public activity |

## Quick Start

```bash
# Install
pip install -e .

# Configure (at minimum: an LLM provider)
tada config set --provider groq --api-key gsk_your_key
tada config set --tavily-api-key tvly_your_key  # optional, strongly recommended

# Analyze a deck
tada run path/to/deck.pdf

# Full audit with all modules
tada audit path/to/deck.pdf

# Batch analyze an entire portfolio
tada batch path/to/decks/

# Compare two versions of the same deck
tada diff path/to/v1.pdf path/to/v2.pdf

# See available commands
tada --help
```

## Commands Reference

### `tada config set`

Configure credentials. All values are written to `~/.FolioPy/config.env` (shared with FolioPy).

```bash
tada config set --provider groq --api-key gsk_abc123
tada config set --tavily-api-key tvly_xyz789
tada config set --model llama-3.3-70b-versatile  # optional model override
```

| Flag | Required | Description |
|------|----------|-------------|
| `--provider` | No | `groq` or `openrouter` (default: `groq`) |
| `--api-key` | No | API key for the LLM provider |
| `--model` | No | Override the default model |
| `--tavily-api-key` | No | Tavily search API key (better results) |

### `tada config show`

Display current configuration with secrets masked.

```bash
tada config show
# Output:
# LLM_PROVIDER=groq
# LLM_API_KEY=gsk...abc
# LLM_MODEL=None
# TAVILY_API_KEY=tvly...xyz
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=eyJ...abc
```

### `tada run <deck.pdf>`

Analyze a single pitch deck. The core pipeline:
1. Parse PDF → per-page text
2. Extract technical AI claims (3-4 categories)
3. Ground each claim against web search
4. Judge each claim → verdict
5. FolioPy cross-reference (always on)
6. Generate markdown report

```bash
# Basic analysis
tada run deck.pdf

# With data moat forensics (verifies "proprietary data" claims)
tada run deck.pdf --data-moat

# With infrastructure flight check (US-India compliance)
tada run deck.pdf --infra

# With talent match (stack detection + contacts)
tada run deck.pdf --talent

# Run everything except audit
tada run deck.pdf --data-moat --infra --talent

# Verbose mode (see every search and fetch)
tada run deck.pdf --verbose
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--data-moat` | — | Run data moat forensics on `data_moat` claims |
| `--infra` | — | Run infrastructure + compliance check |
| `--talent` | — | Run talent match analysis |
| `--verbose` | `-v` | Show debug-level trace output |
| `--repo` | — | (Stretch) GitHub/docs URL for additional grounding |

**Output:** `data/reports/<deck-name>-diligence-<date>.md`

### `tada audit <deck.pdf>`

Convenience command that runs ALL modules: data moat forensics, infrastructure check, talent match, and FolioPy cross-reference.

```bash
tada audit deck.pdf
# Equivalent to: tada run deck.pdf --data-moat --infra --talent
```

**Output:** `data/reports/<deck-name>-audit-<date>.md`

### `tada batch <decks_dir>`

Analyze every PDF in a directory and produce a cross-portfolio map. This is tada's killer feature for systematic diligence.

```bash
tada batch ./potential-deals/
```

**What happens:**
1. Runs the full pipeline on every PDF in the directory
2. Aggregates results into a portfolio-wide matrix
3. Detects cross-portfolio patterns (e.g., "70% of companies claim model architecture advantages")
4. Flags concentration risks (e.g., "3/5 companies claim proprietary data — verify they aren't overlapping")
5. Generates one combined markdown report

**Output:** `data/reports/portfolio-map-<date>.md`

**Sample output table:**
```
| Company       | Claims | Model Arch | Data Moat | Tech Diff | Other | ✅ | ❌ | ⚠️ |
|---------------|--------|-----------|----------|----------|-------|----|----|-----|
| Acme AI       | 4      | 2         | 1        | 1        | 0     | 2  | 1  | 1   |
| Nimbus Labs   | 3      | 1         | 0        | 1        | 1     | 2  | 0  | 1   |
| DeepHealth    | 5      | 1         | 2        | 1        | 1     | 3  | 1  | 1   |
```

### `tada diff <deck_v1.pdf> <deck_v2.pdf>`

Compare claims across two versions of the same deck. Tracks narrative evolution between pitch rounds.

```bash
tada diff seed-deck-v1.pdf seed-deck-v2.pdf
```

**Output:** `data/reports/diff-<deck-name>-<date>.md`

**Sample output signals:**
- `❌ Dropped data moat claim: "proprietary legal contracts dataset"` — possible pivot or reduced confidence
- `➕ New architecture claim: "proprietary foundation model trained from scratch"` — track whether this evolves
- `✏️ 2 claims were reworded` — may indicate messaging refinement or factual correction

## Feature Reference

### 1. Data Moat Forensics (`--data-moat`)

Verifies whether a founder's "proprietary data" claim is actually defensible.

**Pipeline:**
```
Claim: "We have exclusive access to 10M legal contracts"
    │
    ├──► HuggingFace datasets API: search "legal contracts"
    │     └── Finds: "legal-contracts-corpus" (HF), "CaseLaw" (web)
    │
    ├──► Web search: fine-tuned models on legal text
    │     └── Finds: 3 open-source legal fine-tunes achieving 89+% accuracy
    │
    └──► LLM strategic verdict
          └── "Their data is replicable from SEC EDGAR + PACER.
                Public fine-tunes achieve 89% of their claimed accuracy.
                Suggestion: connect them with a data-labeling vendor
                to build a truly proprietary feedback loop."
```

**Report section appears in-output when `--data-moat` is used.**

### 2. Infrastructure Flight Check (`--infra`)

Checks US-India cross-border regulatory and infrastructure risks.

**What it checks:**
- **BIS Export Controls** — Are H100/A100 GPUs used by an Indian-domiciled entity?
- **India DPDP Act** — Are US and Indian user data shards segregated? Cross-border data flows compliant?
- **US State AI Laws** — CCPA, Colorado AI Act exposure?
- **Data Residency** — Training region != serving region?

**Sample report output:**
```
🟡 BIS Export Controls (WARNING)
   - Company uses A100 GPUs on AWS US-East
   - Indian-domiciled entity → possible export restriction
   - Recommendation: Confirm entity structure with legal counsel

🔴 India DPDP Act (CRITICAL)
   - US customer data stored in AWS Mumbai without sharding
   - Recommendation: Set up data segregation proxy layer before US beta
```

**Report section appears when `--infra` is used.**

### 3. Talent Match (`--talent`)

Matches detected tech stack against your contacts network.

**How it works:**
1. Searches web for company's tech stack (GitHub repos, job posts, "powered by" badges)
2. Reads `data/contacts.csv` for expertise + availability
3. Scores matches by keyword overlap
4. Returns top 5 matches with recommendations

**Contacts CSV format (`data/contacts.csv`):**
```
name,expertise,past_companies,availability
Sarah Chen,vLLM;PyTorch;Ray;Distributed Training;CUDA;Kubernetes,Anyscale;NVIDIA,Consulting (10hrs/week)
```

If no contacts file exists, synthetic demo contacts are shown automatically.

**Report section appears when `--talent` is used.**

### 4. FolioPy Cross-Reference (always on)

If FolioPy's Supabase is configured and the company is being tracked, the report includes a cross-reference section showing what public monitoring has already observed.

**Report section always included (will say "not tracked" if not found).**

### 5. Batch Portfolio Mapping (`tada batch`)

Aggregates multiple deck analyses into one portfolio view. Detects:
- Which claim categories are over-represented
- Which companies have contradicted claims needing follow-up
- Concentration risks (e.g., too many companies claiming the same moat)

### 6. Deck Diffing (`tada diff`)

Compares two versions of a deck and classifies every claim change. Uses word-overlap similarity to detect reworded claims. Generates human-readable signals.

## Output Format

All reports are markdown files in `data/reports/`.

| Command | Output file | Contents |
|---------|-------------|----------|
| `tada run` | `<deck>-diligence-<date>.md` | Claims + verdicts + evidence + optional module sections |
| `tada audit` | `<deck>-audit-<date>.md` | Same as run but includes all module sections |
| `tada batch` | `portfolio-map-<date>.md` | Cross-portfolio matrix + patterns + risks |
| `tada diff` | `diff-<deck>-<date>.md` | Change summary + per-claim breakdown + signals |

Report structure (verbose example):
```markdown
# Diligence Report: acme-ai-deck.pdf
**Generated:** 2026-07-08 18:30
**Claims analyzed:** 4

---

## Claim 1: Proprietary foundation model trained from scratch
- **Category:** `model_architecture`
- **Source Slide:** Page 3
- **Verdict:** **❌ Contradicted**

### Reasoning
The company's own engineering blog describes fine-tuning LLaMA-2-7B...

### Evidence
1. **Contradicts claim**
   - Source: https://acme.ai/blog/building-our-ai
   - Excerpt: "We fine-tuned LLaMA-2-7B on our proprietary dataset..."

---

## FolioPy Cross-Reference
✅ **Company found in FolioPy portfolio**
- **Name:** Acme AI
- **URL:** https://acme.ai
- **Last checked:** 2026-07-01

### Recent Monitoring Events
- [launch] Launched beta product v2
- [hiring] Posted ML Engineer role

---

## Data Moat Forensics
...

## Infrastructure Flight Check
...

## Talent Match
...
```

## Installation Details

### Prerequisites

- Python >= 3.10
- pip

### Step-by-step

```bash
# 1. Clone/go to project
cd project_tada

# 2. Install package and dependencies
pip install -e .

# 3. Configure LLM provider (Groq is free: https://console.groq.com)
tada config set --provider groq --api-key gsk_your_key_here

# 4. (Optional but recommended) Configure Tavily for better search
tada config set --tavily-api-key tvly_your_key_here

# 5. (Optional) Configure FolioPy cross-reference
tada config set --supabase-url https://your-project.supabase.co --supabase-key your_key

# 6. Verify it works
tada --help
tada config show
```

### Tavily Setup

1. Sign up at [https://tavily.com](https://tavily.com)
2. Get your API key
3. `tada config set --tavily-api-key tvly_your_key`

Tavily gives you much better search results than the free DuckDuckGo fallback — particularly important for infrastructure detection and fine-tune comparison searches.

### Using with FolioPy

tada shares `~/.FolioPy/config.env` with FolioPy. If you've already configured FolioPy, tada inherits its `LLM_PROVIDER`, `LLM_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and `TAVILY_API_KEY` automatically.

## Configuration File

All config lives at `~/.FolioPy/config.env`:

```env
LLM_PROVIDER=groq
LLM_API_KEY=gsk_your_key_here
LLM_MODEL=
TAVILY_API_KEY=tvly_your_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ_your_key_here
```

You can set values with `tada config set` or edit the file directly.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_claim_extractor.py -v
```

## Project Structure

```
project_tada/
├── core/                       # Shared with FolioPy
│   ├── config.py               # Config reader/writer
│   ├── llm.py                  # LLM wrapper (Groq/OpenRouter)
│   ├── trace.py                # Rich console tracer
│   ├── research.py             # Tavily + DuckDuckGo search
│   └── splash.py               # Splash screen
├── tada/                       # Domain logic
│   ├── models.py               # All pydantic models
│   ├── cli.py                  # CLI entry points
│   ├── deck_parser.py          # PDF → text
│   ├── claim_extractor.py      # LLM → claims
│   ├── grounding.py            # Search → evidence
│   ├── verdict.py              # LLM → verdicts
│   ├── report.py               # Markdown renderer
│   ├── dataset_forensics.py    # Data moat verification
│   ├── infrastructure.py       # Infra + compliance
│   ├── talent.py               # Stack + contacts matching
│   ├── foliopy_bridge.py       # FolioPy cross-ref
│   ├── batch.py                # Portfolio mapping
│   └── diffing.py              # Deck diffing
├── data/
│   ├── contacts.csv            # Talent network
│   └── reports/                # Output reports
├── tests/
│   └── test_claim_extractor.py
├── pyproject.toml
├── requirements.txt
├── README.md
└── DEVELOPER.md                # Full developer documentation
```

## Limitations

- **Claim extraction quality** depends on the LLM. It may miss subtle claims or hallucinate categories.
- **Grounding depth** is limited by what's publicly searchable. Private/pre-announcement signals won't be found.
- **Word-overlap diffing** is primitive — semantically identical claims with different wording show as "added" + "removed" instead of "unchanged."
- **Contacts CSV** must be manually maintained for the talent feature to be useful. Synthetic fallbacks are for demo only.
- **FolioPy integration** requires Supabase credentials and is read-only (tada doesn't write to FolioPy's DB).
- **Regulatory accuracy** depends on the LLM's knowledge of current laws. Always verify compliance flags with a real lawyer.

## License

Internal tool for Together Fund technical intern take-home.
