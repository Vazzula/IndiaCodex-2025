# aegis_backend/app/schemas/asset_tracking.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
import datetime


# --- Schema for creating a new tracking event ---
# This defines the shape of the JSON body for our POST request.
class AssetTrackingCreate(BaseModel):
    asset_id: Optional[UUID] = Field(
        None,
        description="The unique identifier of the asset being tracked. Can be null for general events (e.g., environmental checks).",
    )
    sensor_id: UUID = Field(
        ...,  # ... means this field is required
        description="The unique identifier of the sensor that generated this event.",
    )
    event_type: str = Field(
        ...,
        description="A string representing the type of event (e.g., 'RFID_SCAN', 'BIOMETRIC_SUCCESS').",
        example="RFID_SCAN",
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="A JSON object containing specific details about the event.",
        example={"direction": "out", "gate": "A"},
    )
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        description="The timestamp of the event. Defaults to the current UTC time if not provided.",
    )


# --- Schema for returning a created tracking event ---
# This defines the shape of the JSON response.
class AssetTrackingInDB(AssetTrackingCreate):
    id: int = Field(..., description="The unique database ID of the event log.")

    class Config:
        orm_mode = True  # Allows the model to be created from a SQLAlchemy object
