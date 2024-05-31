from fastapi import FastAPI, Depends, HTTPException
from typing import List
from bson import ObjectId

from .schemas import Url, UrlCreate
from .services.url_service import UrlService, get_url_service, UrlNotValidException, UrlAlreadyExistsException
from .services.auth import JWTBearer
from .services.database import database_service
from .services.http_service import http_service

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    # Initialize the database connection on startup
    await database_service.connect()
    # Initialize the HTTP service session on startup
    await http_service.connect()


@app.on_event("shutdown")
async def shutdown_event():
    # Close the database connection on shutdown
    await database_service.disconnect()
    # Close the HTTP service session on shutdown
    await http_service.disconnect()


@app.get('/urls/{id}', response_model=Url)
async def read(
        url_id: str,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    try:
        object_id = ObjectId(url_id)  # Convert string to ObjectId
    except Exception:
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
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    try:
        updated_url = await url_service.update(object_id, update_data, owner_id)
    except (UrlAlreadyExistsException, UrlNotValidException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if updated_url is None:
        raise HTTPException(status_code=404, detail=f'Url with id={url_id} not found')
    return updated_url


@app.post('/urls', response_model=Url)
async def create(
        create_data: UrlCreate,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    try:
        url = await url_service.create(create_data, owner_id)
    except (UrlAlreadyExistsException, UrlNotValidException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return url


@app.delete('/urls/{id}')
async def delete(
        url_id: str,
        owner_id: str = Depends(JWTBearer()),
        url_service: UrlService = Depends(get_url_service)
):
    try:
        object_id = ObjectId(url_id)  # Convert string to ObjectId
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    is_deleted = await url_service.delete(object_id, owner_id)
    if not is_deleted:
        raise HTTPException(status_code=404, detail=f'Url with id={url_id} not found')
