"""Translation service using DashScope machine translation API."""
from __future__ import annotations

import json
import logging
import os
from urllib import error, request

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)

logger = logging.getLogger(__name__)

TRANSLATION_API_URL = os.getenv(
    "TRANSLATION_API_URL",
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/machine-translation",
)
"""Base URL for the machine translation endpoint."""

TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "")
"""API key used for the translation service."""

TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "qwen-mt-lite")
"""Default translation model identifier."""

TRANSLATION_TIMEOUT = int(os.getenv("TRANSLATION_API_TIMEOUT", "20"))
"""Request timeout (seconds) when communicating with translation APIs."""


def translate_text(text: str, *, source_language: str, target_language: str) -> str | None:
    """Translate the given text and return translated output if available."""

    if not TRANSLATION_API_KEY:
        logger.warning("translation disabled: TRANSLATION_API_KEY is not configured")
        return None
    payload = json.dumps(
        {
            "task": "translation",
            "model": TRANSLATION_MODEL,
            "input": {
                "source_language": source_language,
                "target_language": target_language,
                "text": text,
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    url = TRANSLATION_API_URL
    if "task=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}task=translation"
    req = request.Request(
        url=url,
        data=payload,
        headers={
            "Authorization": f"Bearer {TRANSLATION_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=TRANSLATION_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        logger.error("translation request failed: %s", body)
        return None
    except error.URLError as exc:
        logger.error("translation service unreachable: %s", exc)
        return None
    output = data.get("output")
    if isinstance(output, dict):
        translations = output.get("translations")
        if isinstance(translations, list) and translations:
            candidate = translations[0]
            if isinstance(candidate, dict):
                translated = candidate.get("translation")
                if translated:
                    return str(translated)
        direct_text = output.get("text")
        if direct_text:
            return str(direct_text)
    translated = data.get("translation")
    if translated:
        return str(translated)
    logger.error("unexpected translation response: %s", data)
    return None
