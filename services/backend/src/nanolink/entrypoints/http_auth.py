from typing import Annotated

from fastapi import Depends, Header, Request

from nanolink.domain.errors import NotAuthenticated
from nanolink.domain.ports import TokenVerifier
from nanolink.domain.principals import Principal

ACCESS_TOKEN_HEADER = "X-Forwarded-Access-Token"


def request_verifier(request: Request) -> TokenVerifier:
    verifier: TokenVerifier = request.app.state.verifier
    return verifier


async def current_principal(
    verifier: Annotated[TokenVerifier, Depends(request_verifier)],
    access_token: Annotated[str | None, Header(alias=ACCESS_TOKEN_HEADER)] = None,
) -> Principal:
    if not access_token:
        raise NotAuthenticated
    return await verifier.verify(access_token)


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]
