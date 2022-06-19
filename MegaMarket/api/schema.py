from __future__ import annotations

import re
from datetime import datetime
from enum import Enum, unique

from pydantic import BaseModel, validator

from .exceptions import InvalidUUID, InvalidDateFormat

UUID_64_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$'


@unique
class ShopUnitType(Enum):
    offer = "OFFER"
    category = "CATEGORY"


class ShopUnit(BaseModel):
    id: str
    name: str
    date: str
    parentId: str | None = None
    type: ShopUnitType
    price: int = None
    children: list[ShopUnit] = []


class ShopUnitImport(BaseModel):
    id: str
    name: str
    parentId: str = None
    type: ShopUnitType
    price: int = None

    @validator("id")
    def validate_uuid(cls, id: str):
        if not re.fullmatch(UUID_64_pattern, id):
            raise InvalidUUID


class ShopUnitImportRequest(BaseModel):
    items: list[ShopUnitImport]
    updateDate: str

    @validator("updateDate")
    def check_iso(cls, date: str):
        try:
            new_date: datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            raise InvalidDateFormat


class ShopUnitStatisticUnit(BaseModel):
    id: str
    name: str
    parentId: str = None
    type: ShopUnitType
    price: int = None
    date: str


class ShopUnitStatisticResponse(BaseModel):
    items: list[ShopUnitStatisticUnit] = []


class Error(BaseModel):
    code: int
    message: str
