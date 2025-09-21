from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func

from src.database.core import Base


class LocationNameEnum(enum.Enum):
    VAULT = "VAULT"
    TRANSFER_ZONE = "TRANSFER_ZONE"
    ANTECHAMBER = "ANTECHAMBER"
    VIEWING_ROOM_1 = "VIEWING_ROOM_1"
    VIEWING_ROOM_2 = "VIEWING_ROOM_2"


class Location(Base):
    __tablename__ = "locations"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    name = Column(
        ENUM(LocationNameEnum, name="location_name_enum", create_type=False),
        nullable=False,
        unique=True,
    )
    description = Column(Text)
