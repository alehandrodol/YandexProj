from __future__ import annotations

import re
from datetime import datetime
from enum import Enum, unique

from pydantic import BaseModel, validator

from .exceptions import ElementIdException, InvalidDateFormat, IdExceptionsTypes

UUID_64_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$'


@unique
class ShopUnitType(Enum):
    offer = "OFFER"
    category = "CATEGORY"

    def __str__(self):
        return self.value


class ShopUnit(BaseModel):
    id: str
    name: str
    date: str
    parentId: str | None = None
    type: ShopUnitType
    price: int | None = None
    children: list[ShopUnit] | None

    class Config:
        json_encoders = {
            ShopUnitType: lambda v: str(v)
        }


class ShopUnitImport(BaseModel):
    id: str
    name: str
    parentId: str = None
    type: ShopUnitType
    price: int = None

    @validator("id")
    def validate_uuid(cls, id: str):
        if not re.fullmatch(UUID_64_pattern, id):
            raise ElementIdException(IdExceptionsTypes.uuid)
        return id


class ShopUnitImportRequest(BaseModel):
    items: list[ShopUnitImport]
    updateDate: str

    @validator("updateDate")
    def check_iso(cls, date: str):
        try:
            new_date: datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            raise InvalidDateFormat
        return date


class ShopUnitStatisticUnit(BaseModel):
    id: str
    name: str
    parentId: str = None
    type: ShopUnitType
    price: int = None
    date: str

    class Config:
        json_encoders = {
            ShopUnitType: lambda v: str(v)
        }


class ShopUnitStatisticResponse(BaseModel):
    items: list[ShopUnitStatisticUnit] = []


class Error(BaseModel):
    code: int
    message: str
