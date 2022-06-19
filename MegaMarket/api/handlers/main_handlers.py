import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import asc
from sqlalchemy.orm import Session

from api.exceptions import InvalidImport, ElementIdException, IdExceptionsTypes
from api.schema import ShopUnitImportRequest, ShopUnitStatisticResponse, ShopUnitStatisticUnit, ShopUnitImport, ShopUnitType, ShopUnit, Error
from api.service_funcs import from_pyschema_to_db_schema, add_and_refresh_db, delete_all_children, get_all_children, get_category_price, get_element_with_validation, update_parents
from db.main import get_db
from db.schema import ShopUnitsDB, ShopUnitUpdatesDB

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

    get_node: dict[int, dict[str, Any]] = \
        {
            200: {"model": ShopUnit, "description": "Информация об элементе."},
            400: {"model": Error, "description": "Невалидная схема документа или входные данные не верны."},
            404: {"model": Error, "description": "Категория/товар не найден."}
        }

    sales: dict[int, dict[str, Any]] = \
        {
            200: {"model": ShopUnitStatisticResponse, "description": "Список товаров, цена которых была обновлена."},
            400: {"model": Error, "description": "Невалидная схема документа или входные данные не верны."}
        }

    node_stats: dict[int, dict[str, Any]] = \
        {
            200: {"model": ShopUnitStatisticResponse, "description": "Список товаров, цена которых была обновлена."},
            400: {"model": Error, "description": "Некорректный формат запроса или некорректные даты интервала."},
            404: {"model": Error, "description": "Категория/товар не найден."}
        }


@router.post("/imports", responses=MyResponses.imports)
async def make_import(items: ShopUnitImportRequest,
                      db: Session = Depends(get_db)) -> str | JSONResponse:
    request_ids = {}
    res_list: list[ShopUnitsDB] = []
    for item in items.items:
        item: ShopUnitImport = item
        if item.id in request_ids.keys():
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": f"Данный id={item.id} встретился больше одного раза."})
        item_from_fb: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == item.id).first()
        request_ids[item.id] = item.type if item_from_fb is None else item_from_fb.type

    for item in items.items:
        item: ShopUnitImport = item
        try:
            item: ShopUnitsDB = from_pyschema_to_db_schema(item, items.updateDate, request_ids, db)
            res_list.append(item)
        except InvalidImport as e:
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": e.message})
    for unit in res_list:
        if unit.parent_category is not None:
            update_parents(unit.parent_category, items.updateDate, db)
        add_and_refresh_db(unit, db)
    return status.HTTP_200_OK


@router.delete("/delete/{id}", responses=MyResponses.delete)
def delete_element(id: str, db: Session = Depends(get_db)) -> str | JSONResponse:
    element: ShopUnitsDB = get_element_with_validation(element_id=id, db=db)

    delete_all_children(elem_id=id, db=db)
    db.delete(element)
    db.commit()

    return status.HTTP_200_OK


@router.get("/nodes/{id}", responses=MyResponses.get_node)
def get_info_about_element(id: str, db: Session = Depends(get_db)) -> JSONResponse:
    try:
        element: ShopUnitsDB = get_element_with_validation(element_id=id, db=db)
    except ElementIdException as e:
        status_code = 400 if e.type == IdExceptionsTypes.uuid else 404
        return JSONResponse(status_code=status_code,
                            content={"code": status_code, "message": e.message})

    children_list: list[ShopUnit] = get_all_children(id, db)
    res_node: ShopUnit = ShopUnit(
            id=element.id,
            name=element.name,
            date=element.last_update.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            parentId=element.parent_category,
            type=element.type,
            price=element.price if element.type == ShopUnitType.offer else get_category_price(element.id, db, []),
            children=None if element.type == ShopUnitType.offer else children_list
        )
    return JSONResponse(status_code=200, content=json.loads(res_node.json()))


@router.get("/sales", responses=MyResponses.sales)
def info_about_last_updates(date: str, db: Session = Depends(get_db)) -> JSONResponse:
    try:
        new_date: datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        return JSONResponse(status_code=400, content={"code": 400, "message": "Validation Failed"})

    day_ago_time: datetime = new_date - timedelta(hours=24)
    items: list[ShopUnitsDB] = db.query(ShopUnitsDB).filter(ShopUnitsDB.last_update >= day_ago_time).\
        filter(ShopUnitsDB.last_update <= new_date).filter(ShopUnitsDB.type == ShopUnitType.offer).all()
    res_list: list[ShopUnitStatisticUnit] = []
    for item in items:
        new_item: ShopUnitStatisticUnit = ShopUnitStatisticUnit(
            id=item.id,
            name=item.name,
            parentId=item.parent_category,
            type=item.type,
            price=item.price,
            date=item.last_update.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        )
        res_list.append(new_item)
    response = ShopUnitStatisticResponse(items=res_list)
    return JSONResponse(status_code=200, content=json.loads(response.json()))


@router.get("/node/{id}/statistic", responses=MyResponses.node_stats)
def units_updated_in_range(id: str, dateStart: str, dateEnd: str, db: Session = Depends(get_db)) -> JSONResponse:
    try:
        new_date_start: datetime = datetime.strptime(dateStart, "%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        return JSONResponse(status_code=400, content={"code": 400, "message": "Validation Failed"})

    try:
        new_date_end: datetime = datetime.strptime(dateEnd, "%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        return JSONResponse(status_code=400, content={"code": 400, "message": "Validation Failed"})
    items: list[ShopUnitUpdatesDB] = db.query(ShopUnitUpdatesDB).filter(ShopUnitUpdatesDB.unit_id == id).\
        filter(ShopUnitUpdatesDB.date > new_date_start).\
        filter(ShopUnitUpdatesDB.date < new_date_end).order_by(asc(ShopUnitUpdatesDB.update_date)).all()
    res_list: list[ShopUnitStatisticUnit] = []
    for update in items:
        unit: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == update.unit_id).first()
        res_unit: ShopUnitStatisticUnit = ShopUnitStatisticUnit(
            id=unit.id,
            name=update.name,
            parentId=update.parent_category,
            type=unit.type,
            price=update.price,
            date=update.update_date
        )
        res_list.append(res_unit)
    response = ShopUnitStatisticResponse(items=res_list)
    return JSONResponse(status_code=200, content=json.loads(response.json()))
