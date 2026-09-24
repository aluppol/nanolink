from typing import Annotated

from fastapi import Depends, Request

from nanolink.entrypoints.gateway.services import GatewayServices


def gateway_services(request: Request) -> GatewayServices:
    services: GatewayServices = request.app.state.services
    return services


Services = Annotated[GatewayServices, Depends(gateway_services)]
