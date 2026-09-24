from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import StreamingResponse

from nanolink.entrypoints.http_auth import CurrentPrincipal
from nanolink.entrypoints.http_errors import install_error_handlers
from nanolink.entrypoints.http_health import router as health_router
from nanolink.entrypoints.notifier.events import new_listener, result_events
from nanolink.entrypoints.notifier.services import NotifierServices

NotifierServicesOpener = Callable[[], AbstractAsyncContextManager[NotifierServices]]
STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}

router = APIRouter(prefix="/api")


@router.get("/notifications")
async def stream_notifications(request: Request, principal: CurrentPrincipal) -> StreamingResponse:
    services: NotifierServices = request.app.state.services
    events = result_events(services.feed, principal.owner_id, services.public_base_url, new_listener())
    return StreamingResponse(events, media_type="text/event-stream", headers=STREAM_HEADERS)


def create_notifier_app(open_services: NotifierServicesOpener) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with open_services() as services:
            app.state.services = services
            app.state.verifier = services.verifier
            app.state.readiness = services.readiness
            yield

    app = FastAPI(title="NanoLink notification service", version="1.0.0", lifespan=lifespan, openapi_url=None)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(router)
    return app
