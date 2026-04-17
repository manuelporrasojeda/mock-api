"""HTTP routes for the mock API."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Form, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.models.schemas import MockUpstreamErrorResponse, SystemTokenResponse, UserTokenRequest, UserTokenResponse
from app.services.data_loader import DataLoader
from app.services.mock_behavior_service import MockBehaviorService
from app.services.token_service import TokenService

router = APIRouter()
data_loader = DataLoader(settings.data_directory)


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    """Return a simple health check response."""

    return {"status": "ok"}


@router.post(
    "/oauth2/v1/tokens",
    response_model=SystemTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def create_system_token(
    authorization: Annotated[str, Header(alias="Authorization")],
    oam: Annotated[str, Header(alias="oam")],
    app_key: Annotated[str, Header(alias="app-key")],
    grant_type: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    scope: Annotated[str, Form()],
) -> SystemTokenResponse:
    """Return a mocked systemic access token.

    The endpoint validates the request shape and decodes the Basic credentials,
    but it does not enforce real authentication.
    """

    if not oam.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The 'oam' header is required.")

    if not app_key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The 'app-key' header is required.")

    if grant_type != "password":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="grant_type must be 'password'.")

    if not username.strip() or not password.strip() or not scope.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username, password, and scope are required.",
        )

    try:
        TokenService.decode_basic_authorization(authorization)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SystemTokenResponse(
        expires_in=settings.token_expiration_seconds,
        token_type="Bearer",
        refresh_token=TokenService.generate_refresh_token(),
        access_token=TokenService.generate_system_token(),
    )


@router.post(
    "/customTokenOamCustomerUser/v1/token",
    response_model=UserTokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": MockUpstreamErrorResponse,
            "description": "Mocked upstream error for special testing users.",
        }
    },
)
async def create_user_token(
    payload: UserTokenRequest,
    authorization: Annotated[str, Header(alias="Authorization")],
) -> UserTokenResponse | JSONResponse:
    """Return a mocked user token.

    This endpoint intentionally does not verify the system token because the
    mock should stay permissive.
    """

    if not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Authorization header is required.",
        )

    scenario = MockBehaviorService.get_user_token_scenario(payload.userid)
    if scenario is not None:
        if scenario.behavior == "error" and scenario.error is not None:
            return JSONResponse(
                status_code=scenario.error.status_code,
                content=scenario.error.to_payload(),
            )

        if scenario.behavior == "delay" and scenario.delay_seconds is not None:
            await asyncio.sleep(scenario.delay_seconds)

    return UserTokenResponse(access_token=TokenService.generate_user_token(payload.userid))


@router.get(
    "/{path_name}/v5/status",
    status_code=status.HTTP_200_OK,
)
async def get_status_data(
    path_name: str,
    authorization: Annotated[str, Header(alias="Authorization")],
    account_id: Annotated[str, Query(alias="accountId")],
    new_fields_ind: Annotated[bool, Query(alias="newFieldsInd")],
    national_identity_card_nr: Annotated[str, Query(alias="nationalIdentityCardNr")],
) -> dict[str, Any]:
    """Return mocked JSON data loaded from a file selected by ``path_name``."""

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization header must use the Bearer scheme.",
        )

    _ = new_fields_ind

    scenario = MockBehaviorService.get_status_scenario(
        path_name=path_name,
        national_identity_card_nr=national_identity_card_nr,
        account_id=account_id,
    )
    if scenario is not None and scenario.behavior == "delay" and scenario.delay_seconds is not None:
        await asyncio.sleep(scenario.delay_seconds)

    try:
        payload = await asyncio.to_thread(data_loader.load_status_payload, path_name, national_identity_card_nr)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return payload
