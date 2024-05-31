from fastapi import FastAPI, Depends, HTTPException
from typing import List
from bson import ObjectId

from .schemas import Url, UrlCreate
from .services import UrlService, get_url_service
from .auth import JWTBearer

app = FastAPI()


# TODO Error handling, atomic transactions

@app.get('/urls/{id}', response_model=Url)
async def read(
        url_id: str,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    try:
        object_id = ObjectId(url_id)  # Convert string to ObjectId
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    url = await url_service.read(object_id, owner_id)
    if url is None:
        raise HTTPException(status_code=404, detail=f'Url with id={url_id} not found')
    return url


@app.get('/urls/', response_model=List[Url])
async def read_all(
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    urls = await url_service.read_all(owner_id)
    return urls


@app.patch('/urls/{id}', response_model=Url)
async def update(
        url_id: str,
        update_data: UrlCreate,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    try:
        object_id = ObjectId(url_id)  # Convert string to ObjectId
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    updated_url = await url_service.update(object_id, update_data, owner_id)
    if updated_url is None:
        raise HTTPException(status_code=404, detail=f'Url with id={url_id} not found')
    return updated_url


@app.post('/urls', response_model=Url)
async def create(
        create_data: UrlCreate,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    url = await url_service.create(create_data, owner_id)
    return url


@app.delete('/urls/{id}')
async def delete(
        url_id: str,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    try:
        object_id = ObjectId(url_id)  # Convert string to ObjectId
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    is_deleted = await url_service.delete(object_id, owner_id)
    if not is_deleted:
        raise HTTPException(status_code=404, detail=f'Url with id={url_id} not found')
