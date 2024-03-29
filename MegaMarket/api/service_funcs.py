import re

from sqlalchemy.orm import Session

from db.schema import ShopUnitsDB, ShopUnitUpdatesDB
from .exceptions import InvalidImport, ElementIdException, IdExceptionsTypes
from .schema import ShopUnitImport, ShopUnitType, ShopUnit, UUID_64_pattern


def from_pyschema_to_db_schema(item: ShopUnitImport, date: str,
                               id_types_dict: dict[str, ShopUnitType], db: Session) -> ShopUnitsDB:
    """
    Функция, которая валидирует полученный в реквесте юнит, и в случае
    корректности данных возвращет схему длу базы данных
    """

    # Проверка на то существует ли такой юнит уже в БД
    update: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == item.id).first()
    if update is not None:
        if item.type != update.type:  # Если такой юнит уже сущетсвует то изменять его тип запрещено
            raise InvalidImport(message=f"При обновлении нельзя менять тип юнита: id={item.id}")
    if item.parentId is not None:  # Проверка передаётся ли нам какой-то родительский id
        if item.parentId in id_types_dict.keys():  # Проверка был ли такой id в запросе, который нам поступил
            if id_types_dict[item.parentId] != ShopUnitType.category:  # Проверка на то, что родительский элемент категоория
                raise InvalidImport(
                    message=f"Такого родителя не существует или он не является категорией: id={item.id}")
        else:
            parent: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == item.parentId).first()

            # Если в запросе такого элемента не было, то проверяем его наличие в БД и то, что он является категорией
            if parent is None or parent.type != ShopUnitType.category:
                raise InvalidImport(
                    message=f"Такого родителя не существует или он не является категорией: id={item.id}")

    # Валидация цены
    if item.type == ShopUnitType.category and item.price is not None:
        raise InvalidImport(message=f"У категорий не должно быть цены: id={item.id}")
    elif item.type == ShopUnitType.offer and (item.price is None or item.price < 0):
        raise InvalidImport(message=f"У товаров должна быть цена, и она должна быть больше 0: id={item.id}")

    if update is None:  # Создание схемы, если это не обновление
        update: ShopUnitsDB = ShopUnitsDB(
            id=item.id,
            type=item.type,
            name=item.name,
            price=item.price,
            last_update=date,
            parent_category=item.parentId
        )
    else:  # Обновление схемы
        update.name = item.name
        update.price = item.price
        update.last_update = date
        update.parent_category = item.parentId

    return update


def delete_all_children(elem_id: str, db: Session):
    """Функция, которая удаляет всех потомков элемента и все логи об обновлениях в БД"""
    current_children: list[ShopUnitsDB] = db.query(ShopUnitsDB).filter(ShopUnitsDB.parent_category == elem_id).all()
    for child in current_children:
        db.query(ShopUnitUpdatesDB).filter(ShopUnitUpdatesDB.unit_id == child.id).delete()
        db.commit()
        delete_all_children(child.id, db)

    db.query(ShopUnitsDB).filter(ShopUnitsDB.parent_category == elem_id).delete()
    db.commit()
    return


def get_category_price(unit_id: str, db: Session, prices_list: list[int]) -> int | None:
    """
    Данная функция вычисляет цену катерогии, а именно проходит всех потомков,
    и если потомок является товаром заносит его в список,
    изначально нужно передать пустой список
    """
    children_list: list[ShopUnitsDB] = db.query(ShopUnitsDB).filter(ShopUnitsDB.parent_category == unit_id).all()
    for child in children_list:
        if child.type == ShopUnitType.offer:
            prices_list.append(child.price)
        elif child.type == ShopUnitType.category:
            sub_children_list: list[ShopUnitsDB] = db.query(ShopUnitsDB).\
                filter(ShopUnitsDB.parent_category == child.id).all()
            if len(sub_children_list) > 0:
                get_category_price(child.id, db, prices_list)

    return sum(prices_list) // len(prices_list) if len(prices_list) > 0 else None


def get_all_children(element_id: str, db: Session) -> list[ShopUnit]:
    """Функция возвращает всех потомков элемента в виде списка ShopUnit"""
    children: list[ShopUnitsDB] = db.query(ShopUnitsDB).filter(ShopUnitsDB.parent_category == element_id).all()
    res_list: list[ShopUnit] = []
    for child in children:
        sub_children_list: list[ShopUnit] = get_all_children(child.id, db)
        reformat: ShopUnit = ShopUnit(
            id=child.id,
            name=child.name,
            date=child.last_update.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            parentId=child.parent_category,
            type=child.type,
            price=child.price if child.type == ShopUnitType.offer else get_category_price(child.id, db, []),
            children=None if child.type == ShopUnitType.offer else sub_children_list
        )
        res_list.append(reformat)
    return res_list


def get_element_with_validation(element_id: str, db: Session) -> ShopUnitsDB:
    """Данная функция нужна чтоб взять элемент из БД и проверить корректность переданного ID и его наличие в БД"""
    if not re.fullmatch(UUID_64_pattern, element_id):
        raise ElementIdException(IdExceptionsTypes.uuid)
    element: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == element_id).first()
    if element is None:
        raise ElementIdException(IdExceptionsTypes.not_found)
    return element


def update_parents(parent_id: str, date: str, import_id: int, db: Session) -> None:
    """Данна функция обновляет дату всех предков, и создаёт логи об их обновлениях"""
    parent: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == parent_id).first()
    if parent is None:
        return

    parent.last_update = date
    if parent.parent_category is not None:
        update_parents(parent.parent_category, date, import_id, db)
    add_and_refresh_db(parent, db)
    make_update_log(parent, import_id, db)
    return


def make_update_log(inst: ShopUnitsDB, import_id: int, db: Session) -> None:
    """Функция для создания лога об обновлении элемента"""
    check_duplicate: ShopUnitUpdatesDB = db.query(ShopUnitUpdatesDB).filter(ShopUnitUpdatesDB.unit_id == inst.id).\
        filter(ShopUnitUpdatesDB.import_request_id == import_id).first()
    if check_duplicate is not None:  # Проверяем сделали ли мы уже для данного юнит апдейт лог, если да, то пропускаем
        return
    logDB: ShopUnitUpdatesDB = ShopUnitUpdatesDB(
        unit_id=inst.id,
        name=inst.name,
        price=inst.price if inst.type == ShopUnitType.offer else get_category_price(inst.id, db, []),
        parent_category=inst.parent_category,
        update_date=inst.last_update,
        import_request_id=import_id
    )
    add_and_refresh_db(logDB, db)
    return


def add_and_refresh_db(inst: ShopUnitsDB, db: Session) -> None:
    """
    Сервисная функция для отправки элемента в БД и комита, может использоваться
    как для обновления, так и для добавления
    """
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return
