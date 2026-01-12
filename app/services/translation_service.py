"""Translation service using Qwen-MT (DashScope) OpenAI-compatible API.

This module calls the Qwen-MT translation model via the OpenAI-compatible endpoint:

  POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions   (Beijing)
  POST https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions (Intl/Singapore)

Request body (HTTP) uses:
  - model
  - messages: exactly one user message with content = text to translate
  - translation_options: {source_lang, target_lang}

Docs: https://help.aliyun.com/zh/model-studio/machine-translation
"""

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
    # Default to the *full* OpenAI-compatible HTTP endpoint (NOT just base_url).
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
)
"""HTTP endpoint for Qwen-MT OpenAI-compatible chat completions."""

TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "")
"""API key used for the translation service."""

TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "qwen-mt-lite")
"""Default translation model identifier (e.g., qwen-mt-lite / qwen-mt-flash / qwen-mt-plus)."""

TRANSLATION_TIMEOUT = int(os.getenv("TRANSLATION_API_TIMEOUT", "20"))
"""Request timeout (seconds) when communicating with translation APIs."""

TRANSLATION_DEBUG = os.getenv("TRANSLATION_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
"""Enable verbose debug logging (URL, status, truncated response)."""


_LANG_ALIAS: dict[str, str] = {
    # Common ISO-ish codes -> Qwen-MT language names (best-effort)
    "auto": "auto",
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh-hans": "Chinese",
    "zh-hant": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "jp": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
    "pt-br": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
}


def _normalize_lang(lang: str) -> str:
    """Normalize common language codes/names to what Qwen-MT expects."""
    s = (lang or "").strip()
    if not s:
        return "auto"
    key = s.lower().replace("_", "-")
    # If already looks like "English"/"Chinese", keep as-is (but fix "auto").
    if key in _LANG_ALIAS:
        return _LANG_ALIAS[key]
    # Title-case common names; if user passes a supported language name already, it should work.
    return s


def _ensure_openai_endpoint(url: str) -> str:
    """If user provides only base_url .../compatible-mode/v1, append /chat/completions."""
    u = (url or "").strip()
    if not u:
        return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    # Remove trailing slashes for stable matching.
    u_stripped = u.rstrip("/")

    # If they set base_url, promote it to the actual HTTP endpoint.
    if u_stripped.endswith("/compatible-mode/v1"):
        return u_stripped + "/chat/completions"

    return u  # assume already full endpoint


def translate_text(text: str, *, source_language: str, target_language: str) -> str | None:
    """Translate the given text and return translated output if available.

    Returns None if translation is disabled, request fails, or response cannot be parsed.
    """
    if not TRANSLATION_API_KEY:
        logger.warning("translation disabled: TRANSLATION_API_KEY is not configured")
        return None

    cleaned_text = (text or "").strip()
    if not cleaned_text:
        return None

    # Qwen-MT: recommend specifying source language; can set to 'auto' for detection.
    src = _normalize_lang(source_language)
    tgt = _normalize_lang(target_language)

    url = _ensure_openai_endpoint(TRANSLATION_API_URL)

    # OpenAI-compatible HTTP payload (translation_options is top-level for curl/HTTP calls).
    payload_obj = {
        "model": TRANSLATION_MODEL,
        "messages": [{"role": "user", "content": cleaned_text}],
        "translation_options": {"source_lang": src, "target_lang": tgt},
    }
    payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")

    req = request.Request(
        url=url,
        data=payload,
        headers={
            # OpenAI-compatible endpoint uses Bearer token auth.
            "Authorization": f"Bearer {TRANSLATION_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    if TRANSLATION_DEBUG:
        logger.info("translation request url=%s model=%s src=%s tgt=%s", url, TRANSLATION_MODEL, src, tgt)

    try:
        with request.urlopen(req, timeout=TRANSLATION_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
            data = json.loads(raw)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        logger.error("translation request failed (HTTP %s): %s", getattr(exc, "code", "?"), body)
        return None
    except error.URLError as exc:
        logger.error("translation service unreachable: %s", exc)
        return None
    except Exception as exc:
        logger.error("translation unexpected error: %r", exc)
        return None

    # Expected OpenAI-compatible response:
    #   {"choices":[{"message":{"content":"...translated..."}, ...}], ...}
    try:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(msg, dict):
                content = msg.get("content")
                if content:
                    return str(content).strip()
    except Exception:
        # fall through to debug output
        pass

    # Fallbacks (in case response format changes)
    if TRANSLATION_DEBUG:
        preview = json.dumps(data, ensure_ascii=False)[:2000]
        logger.error("unexpected translation response (preview): %s", preview)
    else:
        logger.error("unexpected translation response: %s", data)

    return None
