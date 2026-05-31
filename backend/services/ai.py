"""Optional AI caption/title generation."""

from __future__ import annotations

import httpx

from backend.config import get_settings

settings = get_settings()

ANTHROPIC_HEADERS = {
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}


async def suggest_caption(title: str, platform: str, context: str = "") -> str | None:
    prompt = (
        f"Write a short {platform} caption for a vertical video titled: {title}. "
        f"Context: {context[:500]}. Include 3-5 hashtags. Output caption only."
    )
    if settings.anthropic_configured:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.anthropic_messages_url,
                headers={
                    **ANTHROPIC_HEADERS,
                    "x-api-key": settings.anthropic_auth_token,
                },
                json={
                    "model": settings.anthropic_default_sonnet_model,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code == 200:
                blocks = resp.json().get("content", [])
                for b in blocks:
                    if b.get("type") == "text":
                        return b.get("text", "").strip()
    if settings.openai_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
    return None
