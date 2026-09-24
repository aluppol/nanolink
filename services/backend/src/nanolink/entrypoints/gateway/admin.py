from fastapi import APIRouter, status

from nanolink.domain.links import DEFAULT_PAGE_SIZE, PageRequest
from nanolink.entrypoints.gateway.api import Cursor, Limit
from nanolink.entrypoints.gateway.dependencies import Services
from nanolink.entrypoints.http_auth import CurrentPrincipal
from nanolink.entrypoints.http_views import LinkPageView, link_page_view

router = APIRouter(prefix="/api/admin")


@router.get("/links")
async def list_all_links(
    principal: CurrentPrincipal, services: Services, cursor: Cursor = None, limit: Limit = DEFAULT_PAGE_SIZE
) -> LinkPageView:
    page = await services.moderation.list_page(principal, PageRequest(cursor, limit))
    return link_page_view(page, services.public_base_url)


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def moderate_link(link_id: str, principal: CurrentPrincipal, services: Services) -> None:
    await services.moderation.delete(principal, link_id)
