import os
import json
import time
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from datetime import datetime, timezone

# --- Configuration ---
# Load environment variables from a .env file
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Static IDs (Copy these from your aegis_backup.sql file) ---

# ASSET
ASSET_ID = "a2b3cc56-b8e3-46d8-bcf5-d8f62cc5697a"  # The Dragon Eye Ruby

# CUSTODIANS
CUSTODIAN_ANKIT_ID = "2cff7b3d-c75f-46d3-9c66-9eacf0c2df70"
CUSTODIAN_INDUSREE_ID = "d66d4d40-2a16-425a-b5e1-8b869fa6e179"

# SENSORS (by location)
# VAULT
SENSOR_VAULT_BIOMETRIC = "de6dd560-5068-4d5a-b4ff-b2b576a9e4e4"
SENSOR_VAULT_RFID_EXIT = "c21635f7-c8b4-424f-8e3e-11ffce1b42b7"
SENSOR_VAULT_RFID_ENTER = "d6282176-5e16-4845-8273-bc2c2bd7f9df"
# TRANSFER ZONE
SENSOR_TRANSFER_ZONE_WEIGHT = "84de2743-9ea2-4ead-925d-694e3cdb8f91"
# ANTECHAMBER (Viewing Room)
SENSOR_ANTECHAMBER_SHOWCASE = "5360b308-e571-4c54-bd93-b83ffe0d53b4"
SENSOR_ANTECHAMBER_NFC = "85bb7c8e-d6b8-4e75-8fd0-e235dae7f080"


# --- Simulation Event Definitions ---

# This sequence should be detected by the daemon as a "VAULT_EXIT" state change
VAULT_EXIT_SEQUENCE = [
    {
        "sensor_id": SENSOR_VAULT_BIOMETRIC,
        "event_type": "CUSTODIAN_AUTH_SUCCESS",
        "details": {
            "custodian_id": CUSTODIAN_ANKIT_ID,
            "custodian_name": "Ankit Akkireddy",
            "action": "VAULT_ACCESS_REQUEST",
            "location_name": "VAULT",
        },
    },
    {
        "sensor_id": SENSOR_VAULT_RFID_EXIT,
        "event_type": "ASSET_SCAN",
        "details": {
            "location_from": "VAULT",
            "location_to": "TRANSFER_ZONE",
            "direction": "EXIT",
        },
    },
]

# This sequence should be detected as a "CUSTODY_TRANSFER" to the viewing room
CUSTODY_TRANSFER_SEQUENCE = [
    {
        "sensor_id": SENSOR_TRANSFER_ZONE_WEIGHT,
        "event_type": "WEIGHT_PLATE_STABLE",
        "details": {
            "current_weight_kg": 1.25,
            "asset_id_detected": ASSET_ID,
            "location_name": "TRANSFER_ZONE",
        },
    },
    {
        "sensor_id": SENSOR_ANTECHAMBER_NFC,
        "event_type": "CUSTODIAN_AUTH_SUCCESS",
        "details": {
            "custodian_id": CUSTODIAN_INDUSREE_ID,
            "custodian_name": "Indusree Devulapalli",
            "action": "RECEIVE_ASSET",
            "location_name": "ANTECHAMBER",
        },
    },
    {
        "sensor_id": SENSOR_ANTECHAMBER_SHOWCASE,
        "event_type": "SHOWCASE_SECURED",
        "details": {
            "asset_id": ASSET_ID,
            "showcase_status": "LOCKED",
            "location_name": "ANTECHAMBER",
        },
    },
]

# This sequence should be detected as the start of a "VAULT_RETURN"
VIEWING_FINISH_SEQUENCE = [
    {
        "sensor_id": SENSOR_ANTECHAMBER_SHOWCASE,
        "event_type": "SHOWCASE_OPENED",
        "details": {
            "asset_id": ASSET_ID,
            "showcase_status": "UNLOCKED",
            "custodian_id": CUSTODIAN_INDUSREE_ID,
            "location_name": "ANTECHAMBER",
        },
    },
    {
        "sensor_id": SENSOR_ANTECHAMBER_NFC,
        "event_type": "CUSTODIAN_AUTH_SUCCESS",
        "details": {
            "custodian_id": CUSTODIAN_ANKIT_ID,
            "custodian_name": "Ankit Akkireddy",
            "action": "TRANSFER_ASSET_TO_VAULT",
            "location_name": "ANTECHAMBER",
        },
    },
]

# This sequence completes the "VAULT_RETURN"
VAULT_RETURN_SEQUENCE = [
    {
        "sensor_id": SENSOR_TRANSFER_ZONE_WEIGHT,
        "event_type": "WEIGHT_PLATE_STABLE",
        "details": {
            "current_weight_kg": 0.0,
            "asset_id_detected": None,
            "location_name": "TRANSFER_ZONE",
        },
    },
    {
        "sensor_id": SENSOR_VAULT_RFID_ENTER,
        "event_type": "ASSET_SCAN",
        "details": {
            "location_from": "TRANSFER_ZONE",
            "location_to": "VAULT",
            "direction": "ENTER",
        },
    },
    {
        "sensor_id": SENSOR_VAULT_BIOMETRIC,
        "event_type": "CUSTODIAN_AUTH_SUCCESS",
        "details": {
            "custodian_id": CUSTODIAN_ANKIT_ID,
            "custodian_name": "Ankit Akkireddy",
            "action": "VAULT_SECURE_ASSET",
            "location_name": "VAULT",
        },
    },
]


def insert_event(conn, event_data: dict):
    """Inserts a single tracking event into the database."""
    sql = """
        INSERT INTO public.asset_tracking (asset_id, sensor_id, event_type, "timestamp", details)
        VALUES (%s, %s, %s, %s, %s);
    """
    try:
        with conn.cursor() as cur:
            # Get current time in UTC
            now_utc = datetime.now(timezone.utc)

            # Execute the insert command
            cur.execute(
                sql,
                (
                    ASSET_ID,
                    event_data["sensor_id"],
                    event_data["event_type"],
                    now_utc,
                    Json(event_data["details"]),  # Use psycopg2's Json helper
                ),
            )
        conn.commit()
        print(f"  -> Successfully inserted event: {event_data['event_type']}")
    except Exception as e:
        print(f"  -> FAILED to insert event: {e}")
        conn.rollback()


def run_simulation_cycle(conn):
    """Runs through the entire happy path sequence."""

    all_sequences = {
        "VAULT EXIT": VAULT_EXIT_SEQUENCE,
        "CUSTODY TRANSFER TO VIEWING": CUSTODY_TRANSFER_SEQUENCE,
        "FINISH VIEWING & PREPARE RETURN": VIEWING_FINISH_SEQUENCE,
        "VAULT RETURN": VAULT_RETURN_SEQUENCE,
    }

    for name, sequence in all_sequences.items():
        print(f"\n--- STAGE: {name} ---")
        for event in sequence:
            insert_event(conn, event)
            time.sleep(10)  # 10-second delay between individual sensor events

        print(f"--- STAGE COMPLETE: {name}. Waiting for daemon to process... ---")
        time.sleep(30)  # 30-second delay for the daemon to complete its cycle


def main():
    """Main function to connect to the DB and run the simulation."""
    conn = None
    try:
        print("Starting asset tracking simulation...")
        print("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(DATABASE_URL)
        print("Database connection successful.")

        run_simulation_cycle(conn)

        print("\nSimulation cycle complete.")

    except psycopg2.OperationalError as e:
        print(
            f"Error: Could not connect to the database. Please check your DATABASE_URL in the .env file."
        )
        print(f"Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
