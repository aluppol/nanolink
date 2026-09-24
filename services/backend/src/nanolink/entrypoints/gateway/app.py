from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from nanolink.entrypoints.gateway.admin import router as admin_router
from nanolink.entrypoints.gateway.api import router as api_router
from nanolink.entrypoints.gateway.internal import router as internal_router
from nanolink.entrypoints.gateway.services import GatewayServices
from nanolink.entrypoints.http_errors import install_error_handlers
from nanolink.entrypoints.http_health import router as health_router

GatewayServicesOpener = Callable[[], AbstractAsyncContextManager[GatewayServices]]


def create_gateway_app(open_services: GatewayServicesOpener) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with open_services() as services:
            app.state.services = services
            app.state.verifier = services.verifier
            app.state.readiness = services.readiness
            yield

    app = FastAPI(
        title="NanoLink API gateway",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)
    for router in (health_router, api_router, admin_router, internal_router):
        app.include_router(router)
    return app
