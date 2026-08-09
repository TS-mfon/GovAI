"""Cross-DAO proposal summarizer (the "summarizes proposals across DAOs" feature).

Produces short, neutral, plain-language summaries so token holders can scan governance
activity across every DAO GovAI serves. Uses an OpenAI-compatible endpoint (configurable
base URL for local models).
"""
import os
from openai import OpenAI

SYSTEM = (
    "You are GovAI, an AI governance copilot. Given a DAO proposal title and body, "
    "write a 2-sentence neutral, factual summary a token holder can understand at a "
    "glance. Do not editorialize or predict outcomes."
)


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "sk-no-key"),
        base_url=os.getenv("OPENAI_BASE_URL"),  # e.g. http://localhost:11434/v1
    )


def summarize_one(title: str, body: str) -> str:
    try:
        resp = _client().chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"TITLE: {title}\n\nBODY:\n{body[:4000]}"},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:  # noqa: BLE001 - degrade gracefully for the feed
        return f"[summary unavailable: {e}] {body[:160]}"


def summarize_batch(items: list[dict]) -> dict[int, str]:
    """items: list of {"id": int, "title": str, "body": str"} -> {id: summary}."""
    return {it["id"]: summarize_one(it["title"], it["body"]) for it in items}
