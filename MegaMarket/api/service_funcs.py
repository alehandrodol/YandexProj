from sqlalchemy.orm import Session

from db.schema import ShopUnits
from .exceptions import InvalidImport
from .schema import ShopUnitImport, ShopUnitType


def from_pyschema_to_db_schema(item: ShopUnitImport, date: str,
                               id_types_dict: dict[str, ShopUnitType], db: Session) -> ShopUnits:
    is_update: ShopUnits = db.query(ShopUnits).filter(ShopUnits.id == item.id).first()
    if is_update is not None:
        if item.type != is_update.type:
            raise InvalidImport(message=f"При обновлении нельзя менять тип юнита: id={item.id}")
    if item.parentId is not None:
        if item.parentId in id_types_dict.keys():
            if id_types_dict[item.parentId] != ShopUnitType.category:
                raise InvalidImport(
                    message=f"Такого родителя не существует или он не является категорией: id={item.id}")
        else:
            parent: ShopUnits = db.query(ShopUnits).filter(ShopUnits.id == item.parentId).first()
            if parent is None or parent.type != ShopUnitType.category:
                raise InvalidImport(
                    message=f"Такого родителя не существует или он не является категорией: id={item.id}")
    if item.type == ShopUnitType.category and item.price is not None:
        raise InvalidImport(message=f"У категорий не должно быть цены: id={item.id}")
    elif item.type == ShopUnitType.offer and (item.price is None or item.price < 0):
        raise InvalidImport(message=f"У товаров должна быть цена, и она должна быть больше 0: id={item.id}")
    db_schema = ShopUnits(
        id=item.id,
        type=item.type,
        name=item.name,
        price=item.price,
        last_update=date,
        parent_category=item.parentId
    )

    return db_schema


def delete_all_children(elem_id: str, db: Session):
    current_children: list[ShopUnits] = db.query(ShopUnits).filter(ShopUnits.parent_category == elem_id).all()
    for child in current_children:
        delete_all_children(child.id, db)
    db.query(ShopUnits).filter(ShopUnits.parent_category == elem_id).delete()
    db.commit()
    return


def add_and_refresh_db(inst: ShopUnits, db: Session):
    db.add(inst)
    db.commit()
    db.refresh(inst)
