from .models import FolioPyCrossRef
from core.trace import Tracer
from core.config import load_config


def _try_get_supabase_client():
    try:
        from supabase import create_client
        cfg = load_config()
        if cfg.supabase_url and cfg.supabase_key:
            return create_client(cfg.supabase_url, cfg.supabase_key)
    except Exception:
        pass
    return None


def cross_reference_with_foliopy(company_name: str, tracer: Tracer) -> FolioPyCrossRef:
    tracer.debug(f"cross-referencing with FolioPy for: {company_name}")

    client = _try_get_supabase_client()
    if not client:
        tracer.debug("  FolioPy Supabase not configured — skipping cross-reference")
        return FolioPyCrossRef(
            company_found=False,
            company_name=company_name,
        )

    try:
        res = client.table("companies").select("*").ilike("name", f"%{company_name}%").execute()
        if not res.data:
            res = client.table("companies").select("*").ilike("url", f"%{company_name.lower()}%").execute()
    except Exception:
        tracer.debug("  FolioPy query failed (table may not exist)")
        return FolioPyCrossRef(
            company_found=False,
            company_name=company_name,
        )

    if not res.data:
        tracer.debug("  company not found in FolioPy portfolio")
        return FolioPyCrossRef(
            company_found=False,
            company_name=company_name,
        )

    company = res.data[0]
    tracer.debug(f"  found in FolioPy: {company['name']} ({company.get('url', 'N/A')})")

    events: list[str] = []
    try:
        snap_res = client.table("snapshots").select("events").eq("company_id", company["id"]).order("taken_at", desc=True).limit(1).execute()
        if snap_res.data and snap_res.data[0].get("events"):
            for ev in snap_res.data[0]["events"][:5]:
                events.append(f"[{ev.get('type', 'event')}] {ev.get('summary', '')}")
    except Exception:
        pass

    return FolioPyCrossRef(
        company_found=True,
        company_name=company["name"],
        company_url=company.get("url", ""),
        last_checked=company.get("last_checked", company.get("added_at", "")),
        monitoring_events=events,
        contradictions=[],
    )
