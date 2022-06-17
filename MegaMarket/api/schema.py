from __future__ import annotations
import logging

from enum import Enum, unique
from pydantic import BaseModel, validator
from datetime import datetime


@unique
class ShopUnitType(Enum):
    offer = "offer"
    category = "category"


class ShopUnit(BaseModel):
    id: str
    name: str
    date: str
    parentId: str = None
    type: ShopUnitType
    price: int = None
    children: list[ShopUnit] = []


class ShopUnitImport(BaseModel):
    id: str
    name: str
    parentId: str = None
    type: ShopUnitType
    price: int = None


class ShopUnitImportRequest(BaseModel):
    items: list[ShopUnitImport]
    updateDate: str

    @validator("updateDate")
    def check_iso(cls, date: str):
        try:
            new_date: datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as e:
            raise e


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
