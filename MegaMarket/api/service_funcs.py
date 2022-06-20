import re
from sqlalchemy.orm import Session

from db.schema import ShopUnitsDB, ShopUnitUpdatesDB
from .exceptions import InvalidImport, ElementIdException, IdExceptionsTypes
from .schema import ShopUnitImport, ShopUnitType, ShopUnit, UUID_64_pattern


def from_pyschema_to_db_schema(item: ShopUnitImport, date: str,
                               id_types_dict: dict[str, ShopUnitType], db: Session) -> ShopUnitsDB:
    update: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == item.id).first()
    if update is not None:
        if item.type != update.type:
            raise InvalidImport(message=f"При обновлении нельзя менять тип юнита: id={item.id}")
    if item.parentId is not None:
        if item.parentId in id_types_dict.keys():
            if id_types_dict[item.parentId] != ShopUnitType.category:
                raise InvalidImport(
                    message=f"Такого родителя не существует или он не является категорией: id={item.id}")
        else:
            parent: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == item.parentId).first()
            if parent is None or parent.type != ShopUnitType.category:
                raise InvalidImport(
                    message=f"Такого родителя не существует или он не является категорией: id={item.id}")
    if item.type == ShopUnitType.category and item.price is not None:
        raise InvalidImport(message=f"У категорий не должно быть цены: id={item.id}")
    elif item.type == ShopUnitType.offer and (item.price is None or item.price < 0):
        raise InvalidImport(message=f"У товаров должна быть цена, и она должна быть больше 0: id={item.id}")
    if update is None:
        update: ShopUnitsDB = ShopUnitsDB(
            id=item.id,
            type=item.type,
            name=item.name,
            price=item.price,
            last_update=date,
            parent_category=item.parentId
        )
    else:
        update.name = item.name
        update.price = item.price
        update.last_update = date
        update.parent_category = item.parentId

    return update


def delete_all_children(elem_id: str, db: Session):
    current_children: list[ShopUnitsDB] = db.query(ShopUnitsDB).filter(ShopUnitsDB.parent_category == elem_id).all()
    for child in current_children:
        db.query(ShopUnitUpdatesDB).filter(ShopUnitUpdatesDB.unit_id == child.id).delete()
        db.commit()
        delete_all_children(child.id, db)

    db.query(ShopUnitsDB).filter(ShopUnitsDB.parent_category == elem_id).delete()
    db.commit()
    return


def get_category_price(unit_id: str, db: Session, prices_list: list[int]) -> int:
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
    if not re.fullmatch(UUID_64_pattern, element_id):
        raise ElementIdException(IdExceptionsTypes.uuid)
    element: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == element_id).first()
    if element is None:
        raise ElementIdException(IdExceptionsTypes.not_found)
    return element


def update_parents(parent_id: str, date: str, db: Session) -> None:
    parent: ShopUnitsDB = db.query(ShopUnitsDB).filter(ShopUnitsDB.id == parent_id).first()
    if parent is None:
        return

    parent.last_update = date
    if parent.parent_category is not None:
        update_parents(parent.parent_category, date, db)
    add_and_refresh_db(parent, db)
    make_update_log(parent, db)
    return


def make_update_log(inst: ShopUnitsDB, db: Session) -> None:
    logDB: ShopUnitUpdatesDB = ShopUnitUpdatesDB(
        unit_id=inst.id,
        name=inst.name,
        price=inst.price if inst.type == ShopUnitType.offer else get_category_price(inst.id, db, []),
        parent_category=inst.parent_category,
        update_date=inst.last_update
    )
    add_and_refresh_db(logDB, db)
    return


def add_and_refresh_db(inst: ShopUnitsDB, db: Session) -> None:
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return
