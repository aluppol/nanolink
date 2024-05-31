from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional
from bson import ObjectId


class BaseItemModel(BaseModel):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @model_validator(mode='before')
    def convert_objectid(cls, values):
        if '_id' in values and isinstance(values['_id'], ObjectId):
            values['id'] = str(values['_id'])
        return values



    class Config:
        from_attributes = True
        populate_by_name = True


class UrlBase(BaseModel):
    long_url: str


class UrlCreate(UrlBase):
    pass


class Url(UrlBase, BaseItemModel):
    short_url: str
    owner_id: str

    class Config:
        from_attributes = True
        populate_by_name = True
