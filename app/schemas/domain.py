from datetime import datetime
from pydantic import Field, field_validator
from .base import ORMModel

ALLOWED_LANGUAGE_CODES = {
    "en",
    "zh",
    "zh_tw",
    "ru",
    "ja",
    "ko",
    "es",
    "fr",
    "pt",
    "de",
    "it",
    "th",
    "vi",
    "id",
    "ms",
    "ar",
    "hi",
    "he",
    "ur",
    "bn",
    "pl",
    "nl",
    "tr",
    "km",
    "cs",
    "sv",
    "hu",
    "da",
    "fi",
    "tl",
    "fa",
}

class DomainCreate(ORMModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    language: str | None = Field(None, max_length=10)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in ALLOWED_LANGUAGE_CODES:
            raise ValueError("unsupported language code")
        return normalized

class DomainUpdate(ORMModel):
    name: str | None = Field(None, min_length=1)
    description: str | None = None
    language: str | None = Field(None, max_length=10)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in ALLOWED_LANGUAGE_CODES:
            raise ValueError("unsupported language code")
        return normalized

class DomainOut(ORMModel):
    id: int
    name: str
    description: str | None
    language: str
    created_at: datetime
    updated_at: datetime
