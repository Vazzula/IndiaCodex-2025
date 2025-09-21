import enum

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.sql import func

from src.database.core import Base


class AssetStatusEnum(enum.Enum):
    IN_VAULT = "IN_VAULT"
    IN_TRANSIT_OUT = "IN_TRANSIT_OUT"
    IN_VIEWING = "IN_VIEWING"
    IN_TRANSIT_IN = "IN_TRANSIT_IN"
    RELEASED = "RELEASED"
    FLAGGED_ANOMALY = "FLAGGED_ANOMALY"


class Asset(Base):
    __tablename__ = "assets"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    serial_number = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    attributes = Column(JSONB)
    current_location_id = Column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )
    current_status = Column(
        ENUM(AssetStatusEnum, name="asset_status_enum", create_type=False),
        nullable=False,
        server_default="IN_VAULT",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
