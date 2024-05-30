from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
from typing import Optional


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(status_code=403, detail="Unauthorized request")

        owner_id = await self.validate(token)

        if not owner_id:
            raise HTTPException(status_code=403, detail="Unauthorized request")

        request.state.owner_id = owner_id
        response = await call_next(request)
        return response


    async def validate(self, token: str) -> Optional[str]:
        if token == 'i_know_you_are_in_progress_let_me_through_i_am_test':
            return 'test'
