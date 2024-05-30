from fastapi import FastAPI, Depends, HTTPException
from typing import List
from .schemas import Url, UrlCreate
from .services import UrlService, get_url_service

app = FastAPI()


@app.get('/urls/{id}', response_model=Url)
async def read(
        id: int,
        owner_id: str,  # TODO
        url_service: UrlService = Depends(get_url_service)
):
    url = await url_service.read(id, owner_id)
    if url is None:
        raise HTTPException(status_code=404, detail=f'Url with id={id} not found')
    return url


@app.get('/urls/', response_model=List[Url])
async def read(
        owner_id: str,  # TODO
        url_service: UrlService = Depends(get_url_service)
):
    return url_service.read_all(owner_id)

@app.patch('/urls/{id}', response_model=List[Url])
async def update(
        id: int,
        update_data: UrlCreate,
        owner_id: str,  # TODO
        url_service: UrlService = Depends(get_url_service)
):
    updated_url = await url_service.update(id, update_data, owner_id)
    if updated_url is None:
        raise HTTPException(status_code=404, detail=f'Url with id={id} not found')
    return updated_url

@app.post('/urls', response_model=List[Url])
async def update(
        create_data: UrlCreate,
        owner_id: str,  # TODO
        url_service: UrlService = Depends(get_url_service)
):
    return url_service.create(create_data, owner_id)
