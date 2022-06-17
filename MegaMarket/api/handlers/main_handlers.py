from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from enum import Enum
from typing import Any

from api.schema import ShopUnitImportRequest, ShopUnitImport, Error
from db.main import get_db
from db.schema import ShopUnits
from api.service_funcs import from_pyschema_to_db_schema, add_and_refresh_db
from api.exceptions import InvalidImport


router = APIRouter()


class MyResponses:
    imports: dict[int, dict[str, Any]] = \
        {200: {"description": "Вставка или обновление прошли успешно."},
         400: {"model": Error, "description": "Невалидная схема документа или входные данные не верны."}}


@router.post("/imports", responses=MyResponses.imports)
async def make_import(items: ShopUnitImportRequest,
                      db: Session = Depends(get_db)) -> str | JSONResponse:
    request_ids = []
    res_list: list[ShopUnits] = []
    for item in items.items:
        item: ShopUnitImport = item
        if item.id in request_ids:
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": f"Данный id={item.id} встретился больше одного раза."})
        try:
            item: ShopUnits = from_pyschema_to_db_schema(item, items.updateDate, db)
            res_list.append(item)
            request_ids.append(item.id)
        except InvalidImport as e:
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": e.message})
    for unit in res_list:
        add_and_refresh_db(unit, db)
    return status.HTTP_200_OK

