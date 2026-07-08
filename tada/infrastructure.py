from .models import InfraFinding, ComplianceFlag, InfrastructureReport
from core.trace import Tracer
from core.llm import complete
from core.research import search_tavily, search_web


_TECH_KEYWORDS = {
    "cloud_provider": ["AWS", "Amazon Web Services", "GCP", "Google Cloud", "Azure", "Microsoft Azure", "OCI", "Oracle Cloud"],
    "gpu": ["A100", "H100", "H200", "B100", "V100", "T4", "L4", "MI250", "MI300", "TPU"],
    "framework": ["PyTorch", "TensorFlow", "JAX", "vLLM", "TGI", "Ray", "CUDA", "TRT-LLM"],
    "region": ["us-east", "us-west", "eu-west", "eu-central", "ap-south", "ap-southeast", "Mumbai", "Singapore", "Frankfurt"],
}


def _detect_infra_from_job_posts(company_name: str, tracer: Tracer) -> list[InfraFinding]:
    findings: list[InfraFinding] = []
    queries = [
        f'"{company_name}" job "infrastructure" OR "ML engineer" OR "DevOps"',
        f'"{company_name}" careers GPU OR cloud OR deployment',
    ]

    for query in queries:
        results = search_tavily(query, max_results=5)
        for r in results:
            snippet = r.get("snippet", "") + r.get("content", "")
            found_tech = []
            for category, keywords in _TECH_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in snippet.lower():
                        found_tech.append(kw)
            if found_tech:
                findings.append(InfraFinding(
                    category="infra_from_jobs",
                    detail=f"Found: {', '.join(found_tech[:5])}",
                    source_url=r["url"],
                ))
                tracer.debug(f"  infra signal from {r['url']}: {', '.join(found_tech[:3])}")

    return findings


def _detect_infra_from_github(company_name: str, tracer: Tracer) -> list[InfraFinding]:
    findings: list[InfraFinding] = []
    queries = [
        f'github.com "{company_name}" OR site:github.com "{company_name}" AI',
    ]

    for query in queries:
        results = search_web(query, max_results=5)
        for r in results:
            snippet = r.get("snippet", "") + r.get("body", "")
            if any(kw in snippet for kw in ["requirements.txt", "Dockerfile", "docker-compose", "Makefile", "pyproject.toml"]):
                findings.append(InfraFinding(
                    category="infra_from_github",
                    detail=f"Repo: {r['url']}",
                    source_url=r["url"],
                ))
                tracer.debug(f"  github signal: {r['url']}")

    return findings


def _check_compliance(company_name: str, training_infra: list[InfraFinding], regions: list[str], tracer: Tracer) -> list[ComplianceFlag]:
    flags: list[ComplianceFlag] = []

    infra_text = "\n".join(f"- {f.detail}" for f in training_infra)
    region_text = ", ".join(regions) if regions else "unknown"

    prompt = (
        f"Company: {company_name}\n"
        f"Detected infrastructure:\n{infra_text}\n"
        f"Detected regions: {region_text}\n\n"
        "Check for regulatory compliance issues relevant to an AI startup "
        "operating between the US and India:\n\n"
        "1. BIS export controls: Do they use H100/A100 GPUs? If so, are there export restriction concerns for Indian-domiciled entities?\n"
        "2. India DPDP Act: Are they handling US and Indian user data? Are there cross-border data transfer issues?\n"
        "3. US state AI laws: Any concerns with serving US customers from Indian infrastructure?\n"
        "4. Data residency: Is their data storage compliant with their customer geography?\n\n"
        "For each issue found, output:\n"
        "FLAG: <critical|warning|info> | <regulation> | <detail> | <recommendation>\n\n"
        "Then output a numbered checklist of 3-5 action items the partner should discuss with the founder."
    )

    raw = complete(prompt, system="You are a cross-border regulatory compliance analyst specializing in US-India AI infrastructure.")

    current_flag: ComplianceFlag | None = None
    checklist: list[str] = []
    in_checklist = False

    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("FLAG:"):
            if current_flag:
                flags.append(current_flag)
            parts = line.replace("FLAG:", "").strip().split("|")
            if len(parts) >= 3:
                severity = parts[0].strip().lower()
                if severity not in ("critical", "warning", "info"):
                    severity = "info"
                current_flag = ComplianceFlag(
                    regulation=parts[1].strip() if len(parts) > 1 else "General",
                    severity=severity,
                    detail=parts[2].strip() if len(parts) > 2 else "",
                    recommendation=parts[3].strip() if len(parts) > 3 else "Discuss with founder.",
                )
        elif line.startswith("CHECKLIST:") or line.startswith("1.") and not in_checklist:
            in_checklist = True
        if in_checklist and line and (line[0].isdigit() or line.startswith("-")):
            checklist.append(line.lstrip("1234567890.- "))

    if current_flag:
        flags.append(current_flag)

    if not flags:
        flags.append(ComplianceFlag(
            regulation="General",
            severity="info",
            detail=f"No specific compliance flags detected for {company_name} from public data.",
            recommendation="Proceed with standard legal review.",
        ))

    return flags


def analyze_infrastructure(company_name: str, tracer: Tracer) -> InfrastructureReport:
    tracer.debug(f"infrastructure flight check for: {company_name}")

    job_findings = _detect_infra_from_job_posts(company_name, tracer)
    github_findings = _detect_infra_from_github(company_name, tracer)

    regions = [f.detail for f in job_findings + github_findings if "us-east" in f.detail.lower() or "mumbai" in f.detail.lower() or "ap-south" in f.detail.lower() or "singapore" in f.detail.lower() or "frankfurt" in f.detail.lower() or "eu-west" in f.detail.lower()]
    compliance = _check_compliance(company_name, job_findings + github_findings, regions, tracer)

    all_findings = job_findings + github_findings
    training = [f for f in all_findings if any(kw in f.detail.lower() for kw in ["gpu", "train", "a100", "h100", "v100", "cuda", "pytorch", "tensorflow"])]
    inference = [f for f in all_findings if any(kw in f.detail.lower() for kw in ["vllm", "tgi", "ray", "deploy", "serve", "infer", "triton"])]

    checklist = [f.action for f in compliance] if True else []
    if not training and not inference:
        checklist = [
            f"Ask {company_name} about their training infrastructure (cloud provider, GPU type, region)",
            f"Verify data residency compliance for their target customer geography",
            f"Confirm no BIS export control issues if using restricted GPUs",
        ]

    report = InfrastructureReport(
        company_name=company_name,
        training_infra=training or [InfraFinding(category="training", detail="No training infra detected from public sources", source_url="")],
        inference_infra=inference or [InfraFinding(category="inference", detail="No inference infra detected from public sources", source_url="")],
        compliance_flags=compliance,
        checklist=checklist,
    )

    tracer.debug(f"infrastructure check complete: {len(all_findings)} findings, {len(compliance)} compliance flags")
    return report
