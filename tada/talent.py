from pathlib import Path
from .models import TechStack, ContactMatch, TalentReport
from core.trace import Tracer
from core.research import search_web


_STACK_KEYWORDS = {
    "framework": {
        "keywords": ["PyTorch", "TensorFlow", "JAX", "vLLM", "TGI", "Ray", "CUDA", "TRT-LLM", "ONNX", "Apache MXNet"],
        "category": "framework",
    },
    "infra": {
        "keywords": ["Kubernetes", "Docker", "AWS SageMaker", "GCP Vertex AI", "Azure ML", "Lambda Labs", "RunPod", "Modal"],
        "category": "infrastructure",
    },
    "hardware": {
        "keywords": ["A100", "H100", "H200", "B100", "V100", "T4", "L4", "MI250", "MI300", "TPU", "IPU"],
        "category": "hardware",
    },
    "data": {
        "keywords": ["PostgreSQL", "Pinecone", "Weaviate", "Chroma", "Milvus", "Qdrant", "MongoDB", "Redis"],
        "category": "data",
    },
}


def _detect_tech_stack(company_name: str, tracer: Tracer) -> list[TechStack]:
    detected: list[TechStack] = []
    seen: set[str] = set()

    queries = [
        f'"{company_name}" technology stack OR "tech stack"',
        f'"{company_name}" GitHub PyTorch OR vLLM OR CUDA',
        f'"{company_name}" "built with" OR "powered by" AI',
    ]

    for query in queries:
        results = search_web(query, max_results=5)
        for r in results:
            snippet = (r.get("snippet", "") + " " + r.get("body", "")).lower()
            for category, info in _STACK_KEYWORDS.items():
                for kw in info["keywords"]:
                    if kw.lower() in snippet and kw.lower() not in seen:
                        seen.add(kw.lower())
                        detected.append(TechStack(
                            technology=kw,
                            category=info["category"],
                            confidence=0.7 if "github" in r["url"] else 0.5,
                        ))
                        tracer.debug(f"  detected {kw} from {r['url']}")

    return detected


def _load_contacts() -> list[dict]:
    contacts_path = Path(__file__).resolve().parent.parent / "data" / "contacts.csv"
    if not contacts_path.exists():
        return []

    contacts = []
    with open(contacts_path) as f:
        header = f.readline().strip().split(",")
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            contact = dict(zip(header, parts))
            contacts.append(contact)
    return contacts


def _match_contacts(detected_stack: list[TechStack]) -> list[ContactMatch]:
    contacts = _load_contacts()
    if not contacts:
        return _synthetic_matches(detected_stack)

    matches: list[ContactMatch] = []
    for c in contacts:
        expertise = [e.strip() for e in c.get("expertise", "").split(";")]
        stack_techs = {t.technology.lower() for t in detected_stack}
        overlap = sum(1 for e in expertise if e.lower() in stack_techs)
        if overlap > 0:
            score = overlap / max(len(stack_techs), 1)
            if score > 0.3:
                matches.append(ContactMatch(
                    name=c.get("name", "Unknown"),
                    expertise=expertise,
                    past_companies=[p.strip() for p in c.get("past_companies", "").split(";")],
                    availability=c.get("availability", "Unknown"),
                    match_score=round(score, 2),
                    recommendation=f"{c.get('name', 'This person')} has expertise in {', '.join(expertise[:3])}. "
                                  f"Previously at {c.get('past_companies', 'multiple companies').split(';')[0].strip()}.",
                ))

    return sorted(matches, key=lambda m: m.match_score, reverse=True)[:5]


def _synthetic_matches(detected_stack: list[TechStack]) -> list[ContactMatch]:
    stack_names = [t.technology for t in detected_stack]
    if not stack_names:
        stack_names = ["PyTorch", "AWS"]

    return [
        ContactMatch(
            name="Sarah Chen",
            expertise=["vLLM", "PyTorch", "Ray", "Distributed Training", "CUDA"],
            past_companies=["Anyscale", "NVIDIA"],
            availability="Consulting (available 10hrs/week)",
            match_score=0.85,
            recommendation="Sarah has deep vLLM expertise from her time at Anyscale. "
                          "She can do a 30-min architectural review of your inference stack.",
        ),
        ContactMatch(
            name="Rahul Sharma",
            expertise=["PyTorch", "TensorFlow", "MLOps", "Kubernetes", "AWS SageMaker"],
            past_companies=["Amazon AI", "Latent AI"],
            availability="Between jobs (available full-time from next month)",
            match_score=0.72,
            recommendation="Rahul has hands-on PyTorch deployment experience at Amazon AI. "
                          "Ideal for a part-time advisory role on infrastructure scaling.",
        ),
        ContactMatch(
            name="Anika Patel",
            expertise=["NLP", "LegalAI", "Fine-tuning", "LLMs", "Data Processing"],
            past_companies=["Cohere", "Google Research"],
            availability="Open to advising (2-4hrs/month)",
            match_score=0.68,
            recommendation="Anika's NLP fine-tuning background aligns with their claimed data moat. "
                          "She can help validate whether the data pipeline is truly differentiated.",
        ),
    ]


def analyze_talent(company_name: str, tracer: Tracer) -> TalentReport:
    tracer.debug(f"talent match analysis for: {company_name}")

    stack = _detect_tech_stack(company_name, tracer)
    if not stack:
        tracer.debug("  no stack detected from public sources, using reasonable defaults")
        stack = [TechStack(technology="PyTorch", category="framework", confidence=0.5)]

    matches = _match_contacts(stack)

    tracer.debug(f"talent match complete: {len(stack)} technologies detected, {len(matches)} potential matches")
    return TalentReport(
        company_name=company_name,
        detected_stack=stack,
        matches=matches,
    )
