import datetime
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from src.database.core import get_db  # Corrected import path
from src.database.entities.sensor import Sensor
from src.database.entities.assets import Asset
from src.database.entities.asset_tracking import AssetTracking


class SensorName(str, Enum):
    BMS_VLT_01 = "BMS-VLT-01"
    RFID_VLT_01A = "RFID-VLT-01A"
    RFID_VLT_01B = "RFID-VLT-01B"
    ENV_VLT_T1 = "ENV-VLT-T1"
    ENV_VLT_H1 = "ENV-VLT-H1"
    CAM_TRZ_01 = "CAM-TRZ-01"
    WSP_TRZ_01 = "WSP-TRZ-01"
    SCS_ANT_01 = "SCS-ANT-01"
    NFC_ANT_01 = "NFC-ANT-01"


# This Enum will create a dropdown menu for selecting an asset by its well-known serial number.
class AssetSerialNumber(str, Enum):
    Mogok_Ruby_001 = "Mogok-Ruby-001"
    Muzo_Emerald_001 = "Muzo-Emerald-001"


class AssetTrackingCreate(BaseModel):
    asset_id: Optional[UUID] = None
    sensor_id: UUID
    event_type: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# --- Schema for returning a created tracking event ---
# This defines the shape of the JSON response.
class AssetTrackingInDB(BaseModel):
    id: int
    asset_id: Optional[UUID]
    sensor_id: UUID
    event_type: str
    details: Optional[Dict[str, Any]]
    timestamp: datetime.datetime

    class Config:
        orm_mode = True  # Allows the model to be created from a SQLAlchemy object


router = APIRouter()


@router.post(
    "/trigger/{sensor_name}",
    response_model=AssetTrackingInDB,
    summary="Trigger a Specific Sensor by Name",
    status_code=201,
)
def trigger_sensor_event(
    sensor_name: SensorName,  # Dropdown from Enum
    db: Session = Depends(get_db),
    body: Dict[str, Any] = Body(
        ...,
        example={
            "asset_serial_number": "Patek-5990-1R",
            "details": {"direction": "out"},
        },
    ),
):
    """
    Simulates an event from a specific sensor, chosen from a dropdown list.

    This endpoint validates the chosen sensor and asset against the database
    and then creates a new, real event in the `asset_tracking` log.

    **Request Body Requirements:**
    - **RFID Sensors**: Must include `asset_serial_number`.
    - **Biometric Sensors**: Must include `custodian_id`.
    - **Environmental Sensors**: Must include `details` with readings.
    """
    # 1. DYNAMIC VALIDATION: Get the sensor from the database
    sensor_in_db = db.query(Sensor).filter(Sensor.name == sensor_name.value).first()
    if not sensor_in_db:
        raise HTTPException(
            status_code=404,
            detail=f"Sensor '{sensor_name.value}' not found in the database. The API Enum may be out of date.",
        )

    asset_in_db = None
    event_type = ""
    asset_serial_value = body.get("asset_serial_number")

    # 2. CONTEXT-AWARE VALIDATION: Check body based on sensor type
    if sensor_in_db.sensor_type in ("RFID_GATE", "SMART_SHOWCASE", "NFC_READER"):
        if not asset_serial_value:
            raise HTTPException(
                status_code=422,
                detail="This event type requires an 'asset_serial_number' in the body.",
            )

        # Validate the asset serial number
        asset_in_db = (
            db.query(Asset).filter(Asset.serial_number == asset_serial_value).first()
        )
        if not asset_in_db:
            raise HTTPException(
                status_code=404,
                detail=f"Asset with serial number '{asset_serial_value}' not found.",
            )

        event_type = f"{sensor_in_db.sensor_type}_SCAN"

    elif sensor_in_db.sensor_type == "BIOMETRIC_SCANNER":
        if "custodian_id" not in body:
            raise HTTPException(
                status_code=422,
                detail="This event type requires a 'custodian_id' in the body.",
            )
        event_type = (
            "BIOMETRIC_SUCCESS"
            if body.get("scan_successful", True)
            else "BIOMETRIC_FAILURE"
        )

    elif sensor_in_db.sensor_type == "ENVIRONMENTAL":
        if "details" not in body:
            raise HTTPException(
                status_code=422,
                detail="Environmental sensors require a 'details' object with readings.",
            )
        event_type = "ENV_READING"

    else:  # For CAMERA_MOTION, WEIGHT_PLATE, etc.
        event_type = f"{sensor_in_db.sensor_type}_DETECTED"

    # 3. CREATE THE ASSET TRACKING RECORD
    event_to_create = AssetTrackingCreate(
        sensor_id=sensor_in_db.id,
        asset_id=asset_in_db.id if asset_in_db else None,
        event_type=event_type,
        details=body.get("details"),
    )

    db_event = AssetTracking(**event_to_create.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event
