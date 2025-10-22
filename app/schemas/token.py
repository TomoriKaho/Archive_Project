"""Pydantic schemas for authentication tokens."""
from datetime import datetime

from pydantic import Field

from .base import ORMModel


class Token(ORMModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type, defaults to bearer")


class TokenPayload(ORMModel):
    sub: str = Field(..., description="Subject contained in the JWT")
    exp: datetime
