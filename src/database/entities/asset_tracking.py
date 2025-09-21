from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.database.core import Base


class AssetTracking(Base):
    __tablename__ = "asset_tracking"
    id = Column(BigInteger, primary_key=True)
    asset_id = Column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True, index=True
    )
    sensor_id = Column(
        UUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False, index=True
    )
    event_type = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    details = Column(JSONB)
    state_change_id = Column(
        UUID(as_uuid=True), ForeignKey("state_changes.id"), nullable=True
    )
