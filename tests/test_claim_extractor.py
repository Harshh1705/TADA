import json
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tada.models import Claim
from tada.claim_extractor import extract_claims
from core.trace import Tracer


def _make_tracer():
    return Tracer(verbose=False)


def test_extract_claims_returns_claims():
    pages = [
        (1, "Our proprietary foundation model is trained from scratch on 10M healthcare records."),
        (2, "We achieve 2x better accuracy than GPT-4 on medical benchmarks."),
    ]
    mock_json = json.dumps([
        {
            "id": "c1",
            "category": "model_architecture",
            "statement": "Proprietary foundation model trained from scratch",
            "source_slide": 1,
        },
        {
            "id": "c2",
            "category": "technical_differentiation",
            "statement": "2x better accuracy than GPT-4 on medical benchmarks",
            "source_slide": 2,
        },
    ])

    with patch("tada.claim_extractor.complete", return_value=mock_json):
        claims = extract_claims(pages, _make_tracer())

    assert len(claims) == 2
    assert all(isinstance(c, Claim) for c in claims)
    assert claims[0].category == "model_architecture"
    assert claims[1].category == "technical_differentiation"


def test_extract_claims_empty_on_invalid_json():
    pages = [(1, "Some text about nothing.")]

    with patch("tada.claim_extractor.complete", return_value="not json"):
        claims = extract_claims(pages, _make_tracer())

    assert claims == []


def test_extract_claims_handles_code_fences():
    pages = [(1, "Our model is fine-tuned from LLaMA.")]
    mock_json = '```json\n[{"id": "c1", "category": "model_architecture", "statement": "Fine-tuned from LLaMA", "source_slide": 1}]\n```'

    with patch("tada.claim_extractor.complete", return_value=mock_json):
        claims = extract_claims(pages, _make_tracer())

    assert len(claims) == 1
    assert claims[0].category == "model_architecture"


def test_extract_claims_retries_on_parse_failure():
    pages = [(1, "Test text.")]

    with patch("tada.claim_extractor.complete", side_effect=["bad json", "also bad"]):
        claims = extract_claims(pages, _make_tracer())

    assert claims == []
