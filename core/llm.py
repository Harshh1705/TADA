from openai import OpenAI
from .config import load_config

_PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.0-flash-exp:free",
    },
}


def complete(prompt: str, system: str | None = None, model: str | None = None) -> str:
    cfg = load_config()
    provider = _PROVIDERS.get(cfg.llm_provider)
    if not provider:
        available = list(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider '{cfg.llm_provider}'. Available: {', '.join(available)}"
        )

    client = OpenAI(base_url=provider["base_url"], api_key=cfg.llm_api_key)
    model = model or cfg.llm_model or provider["default_model"]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=0.1
    )
    return resp.choices[0].message.content or ""
