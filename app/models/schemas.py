"""Pydantic schemas used by the API."""

from pydantic import BaseModel, Field


class SystemTokenResponse(BaseModel):
    """Response payload for the systemic token endpoint."""

    expires_in: int = Field(..., examples=[3600])
    token_type: str = Field(..., examples=["Bearer"])
    refresh_token: str
    access_token: str


class UserTokenRequest(BaseModel):
    """Request payload for generating a user token."""

    userid: str = Field(..., min_length=1)


class UserTokenResponse(BaseModel):
    """Response payload for the user token endpoint."""

    access_token: str


class ErrorResponse(BaseModel):
    """Generic error response."""

    detail: str


class MockUpstreamErrorResponse(BaseModel):
    """Mocked error payload that emulates the upstream API format."""

    timestamp: str
    status: int
    error: str
    message: str
    path: str
