import enum

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func

from src.database.core import Base


class StateChangeEventEnum(enum.Enum):
    VAULT_EXIT = "VAULT_EXIT"
    CUSTODY_TRANSFER = "CUSTODY_TRANSFER"
    VAULT_RETURN = "VAULT_RETURN"
    SECURITY_BREACH = "SECURITY_BREACH"
    ENVIRONMENTAL_BREACH = "ENVIRONMENTAL_BREACH"


class StateChange(Base):
    __tablename__ = "state_changes"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    asset_id = Column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False, index=True
    )
    event_type = Column(
        ENUM(StateChangeEventEnum, name="state_change_event_type", create_type=False),
        nullable=False,
    )
    timestamp = Column(DateTime(timezone=True), nullable=False)
    log_bundle_hash = Column(String(64), nullable=False)
    on_chain_tx_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
