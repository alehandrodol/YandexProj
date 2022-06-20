import json
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.exceptions import InvalidImport, ElementIdException, IdExceptionsTypes
from api.schema import ShopUnitImportRequest, ShopUnitImport, ShopUnitType, ShopUnit, Error
from api.service_funcs import from_pyschema_to_db_schema, add_and_refresh_db, delete_all_children, get_all_children, \
    get_category_price, get_element_with_validation, update_parents, make_update_log
from db.main import get_db
from db.schema import ShopUnitsDB, ShopUnitUpdatesDB

router = APIRouter()  # Создание роутера, который хранит все пути в данном файле к ручкам и передаёт в main app


# Класс в котором лежат все модели и описания респонзов
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


@router.post("/imports", responses=MyResponses.imports, tags=["main tasks"])
async def make_import(items: ShopUnitImportRequest,
                      db: Session = Depends(get_db)) -> str | JSONResponse:
    """
    Handler для импорта и обновления элементов таблицы ShopUnitDB,
    которые являются категориями и товарами данного магазина.
    Все юниты проходят валидации и в случае успеха, обновляют таблицу,
    в таблицу ShopUnitUpdatesDB кладётся лог об обновлении каждого элемента для сохранения истории.
    """
    # Словарь со всеми id данного запроса, для валидации повторений и со значениями в виде типа юнита,
    # для поиска родительской категории во время валидации.
    request_ids: dict[str, ShopUnitType] = {}
    res_list: list[ShopUnitsDB] = []  # Список в котором будут лежать отваледированные товары
    for item in items.items:  # Валидация повторений id и заполнения словарь request_ids
        item: ShopUnitImport = item
        if item.id in request_ids.keys():
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": f"Данный id={item.id} встретился больше одного раза."})
        item_from_fb: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == item.id).first()
        request_ids[item.id] = item.type if item_from_fb is None else item_from_fb.type

    for item in items.items:  # Цикол с заключительными валидациями, после чего добавляются в res_list
        item: ShopUnitImport = item
        try:
            item: ShopUnitsDB = from_pyschema_to_db_schema(item, items.updateDate, request_ids, db)
            res_list.append(item)
        except InvalidImport as e:
            return JSONResponse(status_code=400,
                                content={"code": 400, "message": e.message})
    for unit in res_list:  # обновление родителей и добавления/обновление в базу всех элементов из запроса
        add_and_refresh_db(unit, db)
        if unit.parent_category is not None:
            update_parents(unit.parent_category, items.updateDate, db)
    # Создание update логов, нужно вылнять после занесения всех элементов в таблицу для
    # корректного определения цены категорий
    for unit in res_list:
        make_update_log(unit, db)
    return status.HTTP_200_OK


@router.delete("/delete/{id}", responses=MyResponses.delete, tags=["main tasks"])
async def delete_element(id: str, db: Session = Depends(get_db)) -> str | JSONResponse:
    """Handler для удаления юнита и всех его дочерних элементов"""
    try:
        element: ShopUnitsDB = get_element_with_validation(element_id=id, db=db)
    except ElementIdException as e:
        status_code = 400 if e.type == IdExceptionsTypes.uuid else 404
        return JSONResponse(status_code=status_code,
                            content={"code": status_code, "message": e.message})

    db.query(ShopUnitUpdatesDB).filter(ShopUnitUpdatesDB.unit_id == id).delete()
    db.commit()

    delete_all_children(elem_id=id, db=db)
    db.delete(element)
    db.commit()

    return status.HTTP_200_OK


@router.get("/nodes/{id}", responses=MyResponses.get_node, tags=["main tasks"])
async def get_info_about_element(id: str, db: Session = Depends(get_db)) -> JSONResponse:
    """Handler, который возвращает информацию о юните из магазина."""
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
