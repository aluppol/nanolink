from nanolink.application.link_creation import ensure_valid_long_url
from nanolink.domain.errors import LinkNotFound, NotAuthorized
from nanolink.domain.links import Link, LinkPage, PageRequest
from nanolink.domain.ports import AllLinks, LinkCache, LinkEditor, OwnedLinks
from nanolink.domain.principals import Principal


class OwnedLinkManagement:
    def __init__(self, links: OwnedLinks, editor: LinkEditor, cache: LinkCache) -> None:
        self._links = links
        self._editor = editor
        self._cache = cache

    async def list_page(self, principal: Principal, page: PageRequest) -> LinkPage:
        return await self._links.list_owned(principal.owner_id, page)

    async def read(self, principal: Principal, link_id: str) -> Link:
        link = await self._links.find_owned(link_id, principal.owner_id)
        if link is None:
            raise LinkNotFound
        return link

    async def change_long_url(self, principal: Principal, link_id: str, long_url: str) -> None:
        ensure_valid_long_url(long_url)
        link = await self.read(principal, link_id)
        await self._editor.change_long_url(link.id, long_url)
        await self._cache.forget([link.short_code])

    async def delete(self, principal: Principal, link_id: str) -> None:
        link = await self.read(principal, link_id)
        await self._editor.soft_delete(link.id)
        await self._cache.forget([link.short_code])


class LinkModeration:
    def __init__(self, links: AllLinks, editor: LinkEditor, cache: LinkCache) -> None:
        self._links = links
        self._editor = editor
        self._cache = cache

    async def list_page(self, principal: Principal, page: PageRequest) -> LinkPage:
        _ensure_admin(principal)
        return await self._links.list_all(page)

    async def delete(self, principal: Principal, link_id: str) -> None:
        _ensure_admin(principal)
        link = await self._links.find_any(link_id)
        if link is None:
            raise LinkNotFound
        await self._editor.soft_delete(link.id)
        await self._cache.forget([link.short_code])


def _ensure_admin(principal: Principal) -> None:
    if not principal.is_admin:
        raise NotAuthorized
