from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BaseItemModel(BaseModel):
    id: int = Field(..., alias="_id")
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class UrlBase(BaseModel):
    long_url: str


class UrlCreate(UrlBase):
    pass


class Url(UrlBase, BaseItemModel):
    short_url: str
    owner_id: str

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
