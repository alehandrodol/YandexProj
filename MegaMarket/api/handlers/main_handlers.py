import re
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.exceptions import InvalidImport
from api.schema import ShopUnitImportRequest, ShopUnitImport, Error, UUID_64_pattern
from api.service_funcs import from_pyschema_to_db_schema, add_and_refresh_db, delete_all_children
from db.main import get_db
from db.schema import ShopUnits

router = APIRouter()


class MyResponses:
    imports: dict[int, dict[str, Any]] = \
        {
            200: {"description": "Вставка или обновление прошли успешно."},
            400: {"model": Error, "description": "Невалидная схема документа или входные данные не верны."}
        }

    delete: dict[int, dict[str, Any]] = \
        {
            200: {"description": "Удаление прошло успешно."},
            400: {"model": Error, "description": "Невалидная схема документа или входные данные не верны."},
            404: {"model": Error, "description": "Категория/товар не найден."}
        }


@router.post("/imports", responses=MyResponses.imports)
async def make_import(items: ShopUnitImportRequest,
                      db: Session = Depends(get_db)) -> str | JSONResponse:
    request_ids = {}
    res_list: list[ShopUnits] = []
    for item in items.items:
        item: ShopUnitImport = item
        if item.id in request_ids.keys():
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": f"Данный id={item.id} встретился больше одного раза."})
        item_from_fb: ShopUnits = db.query(ShopUnits).filter(ShopUnits.id == item.id).first()
        request_ids[item.id] = item.type if item_from_fb is None else item_from_fb.type

    for item in items.items:
        item: ShopUnitImport = item
        try:
            item: ShopUnits = from_pyschema_to_db_schema(item, items.updateDate, request_ids, db)
            res_list.append(item)
        except InvalidImport as e:
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": e.message})
    for unit in res_list:
        add_and_refresh_db(unit, db)
    return status.HTTP_200_OK


@router.delete("/delete/{id}", responses=MyResponses.delete)
def delete_element(id: str, db: Session = Depends(get_db)) -> str | JSONResponse:
    if re.fullmatch(UUID_64_pattern, id):
        return JSONResponse(status_code=404,
                            content={"code": 400, "message": "Validation Failed"})
    element: ShopUnits = db.query(ShopUnits).filter(ShopUnits.id == id).first()
    if element is None:
        return JSONResponse(status_code=404,
                            content={"code": 404, "message": "Item not found"})

    delete_all_children(elem_id=id, db=db)
    db.delete(element)
    db.commit()

    return status.HTTP_200_OK
