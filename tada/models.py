from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# ── Core diligence models ──

class Claim(BaseModel):
    id: str
    category: Literal["model_architecture", "data_moat", "technical_differentiation", "other"]
    statement: str
    source_slide: int


class Evidence(BaseModel):
    text: str
    source_url: str
    supports: bool | None = None


class Verdict(BaseModel):
    claim: Claim
    evidence: list[Evidence]
    verdict: Literal["supported", "contradicted", "inconclusive"]
    reasoning: str


class DiligenceReport(BaseModel):
    deck_filename: str
    generated_at: datetime
    verdicts: list[Verdict]


# ── Data Moat Forensics ──

class PublicDataset(BaseModel):
    name: str
    source: str
    url: str
    description: str
    similarity_score: float


class FineTuneComparison(BaseModel):
    paper_title: str
    paper_url: str
    dataset_used: str
    reported_accuracy: str
    relevance: str


class DataMoatForensic(BaseModel):
    claimed_data_source: str
    similar_public_datasets: list[PublicDataset]
    fine_tune_comparisons: list[FineTuneComparison]
    verdict: str
    suggestion: str


# ── Infrastructure Flight Check ──

class InfraFinding(BaseModel):
    category: str
    detail: str
    source_url: str


class ComplianceFlag(BaseModel):
    regulation: str
    severity: Literal["critical", "warning", "info"]
    detail: str
    recommendation: str


class InfrastructureReport(BaseModel):
    company_name: str
    training_infra: list[InfraFinding]
    inference_infra: list[InfraFinding]
    compliance_flags: list[ComplianceFlag]
    checklist: list[str]


# ── Talent Match ──

class TechStack(BaseModel):
    technology: str
    category: str
    confidence: float


class ContactMatch(BaseModel):
    name: str
    expertise: list[str]
    past_companies: list[str]
    availability: str
    match_score: float
    recommendation: str


class TalentReport(BaseModel):
    company_name: str
    detected_stack: list[TechStack]
    matches: list[ContactMatch]


# ── Batch Portfolio Map ──

class PortfolioEntry(BaseModel):
    deck_filename: str
    company_name: str
    claim_count: int
    claims_by_category: dict[str, int]
    verdict_summary: dict[str, int]
    key_risks: list[str]


class PortfolioMap(BaseModel):
    generated_at: datetime
    entries: list[PortfolioEntry]
    cross_portfolio_patterns: list[str]
    concentration_risks: list[str]


# ── Deck Diff ──

class ClaimDiff(BaseModel):
    status: Literal["added", "removed", "changed", "unchanged"]
    claim_id: str | None = None
    statement: str
    category: str
    source_slide: int
    previous_statement: str | None = None


class DeckDiffReport(BaseModel):
    v1_filename: str
    v2_filename: str
    generated_at: datetime
    claim_diffs: list[ClaimDiff]
    summary: dict[str, int]
    signals: list[str]


# ── FolioPy cross-reference ──

class FolioPyCrossRef(BaseModel):
    company_found: bool
    company_name: str
    company_url: str | None = None
    last_checked: str | None = None
    monitoring_events: list[str] = []
    contradictions: list[str] = []
