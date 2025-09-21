import enum

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func

from src.database.core import Base


class SensorTypeEnum(enum.Enum):
    BIOMETRIC_SCANNER = "BIOMETRIC_SCANNER"
    RFID_GATE = "RFID_GATE"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    CAMERA_MOTION = "CAMERA_MOTION"
    WEIGHT_PLATE = "WEIGHT_PLATE"
    SMART_SHOWCASE = "SMART_SHOWCASE"
    NFC_READER = "NFC_READER"


class SensorStatusEnum(enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    name = Column(String(100), nullable=False, unique=True)
    sensor_type = Column(
        ENUM(SensorTypeEnum, name="sensor_type_enum", create_type=False), nullable=False
    )
    location_id = Column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True
    )
    status = Column(
        ENUM(SensorStatusEnum, name="sensor_status_enum", create_type=False),
        nullable=False,
        server_default="ONLINE",
    )
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
