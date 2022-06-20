import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import asc
from sqlalchemy.orm import Session

from api.exceptions import ElementIdException, IdExceptionsTypes
from api.schema import ShopUnitStatisticResponse, ShopUnitStatisticUnit, ShopUnitType, Error
from api.service_funcs import get_element_with_validation
from db.main import get_db
from db.schema import ShopUnitsDB, ShopUnitUpdatesDB

router = APIRouter()  # Создание роутера, который хранит все пути в данном файле к ручкам и передаёт в main app


# Класс в котором лежат все модели и описания респонзов
class MyResponses:
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


@router.get("/sales", responses=MyResponses.sales, tags=["additional tasks"])
async def info_about_last_updates(date: str, db: Session = Depends(get_db)) -> JSONResponse:
    """Получение списка **товаров**, цена которых была обновлена за последние 24 часа"""
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


@router.get("/node/{id}/statistic", responses=MyResponses.node_stats, tags=["additional tasks"])
async def units_updated_in_range(id: str, dateStart: str, dateEnd: str, db: Session = Depends(get_db)) -> JSONResponse:
    """Получение статистики (истории обновлений) по товару/категории за заданный полуинтервал [from, to)."""
    try:
        get_element_with_validation(element_id=id, db=db)
    except ElementIdException as e:
        status_code = 400 if e.type == IdExceptionsTypes.uuid else 404
        return JSONResponse(status_code=status_code,
                            content={"code": status_code, "message": e.message})
    try:
        new_date_start: datetime = datetime.strptime(dateStart, "%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        return JSONResponse(status_code=400, content={"code": 400, "message": "Validation Failed"})

    try:
        new_date_end: datetime = datetime.strptime(dateEnd, "%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        return JSONResponse(status_code=400, content={"code": 400, "message": "Validation Failed"})
    items: list[ShopUnitUpdatesDB] = db.query(ShopUnitUpdatesDB).filter(ShopUnitUpdatesDB.unit_id == id).\
        filter(ShopUnitUpdatesDB.update_date >= new_date_start).\
        filter(ShopUnitUpdatesDB.update_date < new_date_end).order_by(asc(ShopUnitUpdatesDB.id)).all()
    res_list: list[ShopUnitStatisticUnit] = []
    for update in items:
        unit: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == update.unit_id).first()
        res_unit: ShopUnitStatisticUnit = ShopUnitStatisticUnit(
            id=unit.id,
            name=update.name,
            parentId=update.parent_category,
            type=unit.type,
            price=update.price,
            date=update.update_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        )
        res_list.append(res_unit)
    response = ShopUnitStatisticResponse(items=res_list)
    return JSONResponse(status_code=200, content=json.loads(response.json()))
