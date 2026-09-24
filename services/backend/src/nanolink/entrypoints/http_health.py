from collections.abc import Sequence

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from nanolink.entrypoints.readiness import ReadinessCheck, all_ready

router = APIRouter()


@router.get("/healthz")
async def report_liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def report_readiness(request: Request) -> JSONResponse:
    checks: Sequence[ReadinessCheck] = request.app.state.readiness
    if await all_ready(checks):
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "not_ready"}, status_code=503)
