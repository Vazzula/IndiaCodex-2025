from sqlalchemy import Column, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from src.database.core import Base


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    triggering_asset_tracking_id = Column(
        BigInteger, ForeignKey("asset_tracking.id"), nullable=False, index=True
    )
    analysis_report = Column(Text)
    manager_plan = Column(Text)
    client_email = Column(Text)
    state_change_id = Column(
        UUID(as_uuid=True),
        ForeignKey("state_changes.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
