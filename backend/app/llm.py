import json
import os
import urllib.request

DEFAULT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def is_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def generate_text(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 300,
    temperature: float = 0.4,
) -> str:
    """Raw urllib call to OpenAI's chat completions endpoint, mirroring
    app.embeddings.openai_embed()'s style rather than adding the full openai
    SDK as a dependency for one call site. Raises on any failure — callers
    are expected to catch and fall back to a deterministic alternative
    (see fingerprint_service, theme_report_service) rather than surface an
    LLM outage to the end user.
    """
    api_key = os.environ["OPENAI_API_KEY"]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"].strip()
