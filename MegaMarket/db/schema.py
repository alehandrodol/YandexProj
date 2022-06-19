from sqlalchemy import Column, Integer, String, DateTime, Enum as PgEnum

from api.schema import ShopUnitType
from main import Base


class ShopUnits(Base):
    __tablename__ = "shop_units"

    id = Column(String, primary_key=True)
    type = Column(PgEnum(ShopUnitType, name="type"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=True)
    last_update = Column(DateTime(timezone=True))
    parent_category = Column(String, nullable=True)

