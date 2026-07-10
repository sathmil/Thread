import json
import os
import urllib.request

DEFAULT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def is_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def chat_completion_raw(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 400,
    temperature: float = 0.3,
) -> dict:
    """Raw urllib call to OpenAI's chat completions endpoint, mirroring
    app.embeddings.openai_embed()'s style rather than adding the full openai
    SDK as a dependency. Returns the full parsed response (not just the
    text) so callers needing tool_calls — see agent_service — get the
    complete message object; generate_text() below is the plain-text
    convenience wrapper most call sites use.
    """
    api_key = os.environ["OPENAI_API_KEY"]
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def generate_text(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 300,
    temperature: float = 0.4,
) -> str:
    """Raises on any failure — callers are expected to catch and fall back
    to a deterministic alternative (see fingerprint_service,
    theme_report_service) rather than surface an LLM outage to the end user.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = chat_completion_raw(messages, model=model, max_tokens=max_tokens, temperature=temperature)
    return payload["choices"][0]["message"]["content"].strip()
