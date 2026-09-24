import hmac
from typing import Annotated

from fastapi import APIRouter, Header

from nanolink.domain.errors import NotAuthenticated
from nanolink.domain.sandbox import DEMO_LINK_SEEDS
from nanolink.entrypoints.gateway.dependencies import Services
from nanolink.entrypoints.http_views import DemoResetView

DEMO_RESET_TOKEN_HEADER = "X-Demo-Reset-Token"

router = APIRouter(prefix="/internal")


@router.post("/demo-reset")
async def reset_demo_sandbox(
    services: Services,
    reset_token: Annotated[str | None, Header(alias=DEMO_RESET_TOKEN_HEADER)] = None,
) -> DemoResetView:
    if not hmac.compare_digest((reset_token or "").encode(), services.demo_reset_token.encode()):
        raise NotAuthenticated
    removed = await services.sandbox.link_count()
    await services.sandbox.reset()
    return DemoResetView(removed=removed, seeded=len(DEMO_LINK_SEEDS))
