from sqlalchemy.orm import Session
from datetime import datetime

from .schema import ShopUnitImport, ShopUnitType
from db.schema import ShopUnits
from .exceptions import InvalidImport


def from_pyschema_to_db_schema(item: ShopUnitImport, date: str, db: Session) -> ShopUnits:
    if item.parentId is not None:
        parent: ShopUnits = db.query(ShopUnits).filter(ShopUnits.id == item.parentId).first()
        if parent is None or parent.type != ShopUnitType.category:
            raise InvalidImport(message=f"Такого родителя не существует или он не является категорией: id={item.id}")
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


def add_and_refresh_db(inst: ShopUnits, db: Session):
    db.add(inst)
    db.commit()
    db.refresh(inst)
