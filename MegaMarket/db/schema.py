from sqlalchemy import Column, Integer, String, DateTime, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import relationship

from api.schema import ShopUnitType
from main import Base


class ShopUnitsDB(Base):
    __tablename__ = "shop_units"

    id = Column(String, primary_key=True)
    type = Column(PgEnum(ShopUnitType, name="type"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=True)
    last_update = Column(DateTime(timezone=True))
    parent_category = Column(String, nullable=True)

    update = relationship("ShopUnitUpdatesDB", back_populates="unit")


class ShopUnitUpdatesDB(Base):
    __tablename__ = "shop_units_update_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(String, ForeignKey("shop_units.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=True)
    parent_category = Column(String, nullable=True)
    update_date = Column(DateTime, nullable=False)

    unit = relationship("ShopUnitsDB", back_populates="update")


