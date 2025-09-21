import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional

from src.services.aegis import config
from src.services.aegis.database import DatabaseService
from src.services.aegis.blockchain_service import BlockchainService


class EventProcessor:
    """
    Analyzes sequences of unprocessed `asset_tracking` events to find "happy path"
    state changes based on the rules in `config.py`.
    """

    def __init__(self, db_service: DatabaseService, bc_service: BlockchainService):
        self.db = db_service
        self.bc = bc_service
        self.rules = config.EVENT_SEQUENCE_RULES

    async def process_events(self, assets: List[Dict], events: List[Dict]):
        """
        Main method to process all unprocessed events. Now asynchronous.
        """
        # --- New Logging Section for Asset Status ---
        print("\n--- AEGIS STATE REPORT ---")
        if not assets:
            print("No active assets found.")
        else:
            moving_assets = []
            stationary_assets = []
            for asset in assets:
                # Assets in a transient state are considered 'moving'
                if asset["current_status"] in ("IN_TRANSIT_OUT", "IN_TRANSIT_IN"):
                    moving_assets.append(
                        f"  -> ID: {asset['id']}, Status: {asset['current_status']}"
                    )
                else:
                    stationary_assets.append(
                        f"  -> ID: {asset['id']}, Status: {asset['current_status']}"
                    )

            print(f"Total Active Assets: {len(assets)}")
            if stationary_assets:
                print("\nStationary Assets:")
                for a in stationary_assets:
                    print(a)
            if moving_assets:
                print("\nAssets in Transit:")
                for a in moving_assets:
                    print(a)
        print("--------------------------\n")

        if not events:
            return

        events_by_asset = defaultdict(list)
        for event in events:
            # Ensure asset_id is a string, as it comes from the DB
            events_by_asset[str(event["asset_id"])].append(event)

        asset_map = {str(asset["id"]): asset for asset in assets}

        for asset_id, asset_events in events_by_asset.items():
            asset_info = asset_map.get(asset_id)
            if not asset_info:
                continue

            current_status = asset_info["current_status"]
            possible_outcomes = self.rules.get(current_status, {})

            for new_state, required_sequence in possible_outcomes.items():
                # This check will now correctly find sequences and handle bundling
                await self._check_for_sequence(
                    asset_id, asset_events, new_state, required_sequence
                )

    def _get_event_location(self, details: Dict[str, Any]) -> Optional[str]:
        """
        Contextually determines the most relevant location for an event.
        For movement events (like scans), the destination ('location_to') is prioritized.
        For static events (like auth), the specific location name is used.
        """
        # For movement events, the destination is the key piece of context.
        if "direction" in details and details.get("direction") in ("EXIT", "ENTER"):
            return details.get("location_to") or details.get("location_from")

        # For all other events, use the specific location or fall back.
        return (
            details.get("location_name")
            or details.get("location_to")
            or details.get("location_from")
        )

    async def _check_for_sequence(
        self, asset_id, available_events, new_state, required_sequence
    ):
        """
        Checks if the required sequence of events exists for an asset.
        This version correctly checks for a sub-sequence and bundles only the relevant events.
        """
        # --- BUG FIX: Replaced simple 'or' logic with a context-aware function ---
        available_event_types = [
            (e["event_type"], self._get_event_location(e.get("details", {})))
            for e in available_events
        ]

        len_req = len(required_sequence)
        if not len_req:
            return  # Cannot match an empty sequence

        for i in range(len(available_event_types) - len_req + 1):
            # Check if the slice of available events matches the required sequence
            if available_event_types[i : i + len_req] == required_sequence:
                print(
                    f"PROCESSOR: Found valid event sequence for '{new_state}' for asset {asset_id}"
                )

                # Bundle *only* the events that make up the matched sequence
                event_bundle = available_events[i : i + len_req]

                await self._trigger_state_change(asset_id, new_state, event_bundle)

                # After processing a sequence, we must stop to prevent double-processing.
                return

    def _calculate_bundle_hash(self, events: List[Dict[str, Any]]) -> str:
        """Calculates a SHA-256 hash of a list of event dictionaries."""
        bundle_string = "".join(
            sorted([json.dumps(event, default=str) for event in events])
        )
        return hashlib.sha256(bundle_string.encode()).hexdigest()

    async def _trigger_state_change(
        self, asset_id: str, new_state: str, event_bundle: List[Dict]
    ):
        """Orchestrates the creation of a new state change. Now asynchronous."""
        if not event_bundle:
            print(
                f"ERROR: Attempted to trigger state change for {asset_id} with an empty event bundle."
            )
            return

        final_event = event_bundle[-1]
        timestamp = datetime.fromisoformat(final_event["timestamp"])

        # --- CHANGE: Get the sensor ID from the final event to determine the new location ---
        final_sensor_id = final_event.get("sensor_id")

        log_bundle_hash = self._calculate_bundle_hash(event_bundle)

        on_chain_tx_id = await self.bc.record_state_change(
            asset_id=asset_id,
            event_type=new_state,
            log_bundle_hash=log_bundle_hash,
            timestamp=timestamp,
        )

        if not on_chain_tx_id:
            print(
                f"ERROR: Failed to get on-chain TX ID for '{new_state}' on asset {asset_id}. Aborting DB commit."
            )
            return

        event_ids_to_link = [event["id"] for event in event_bundle]
        new_asset_status = config.NEXT_ASSET_STATUS_MAP[new_state]

        # --- CHANGE: Pass the final_sensor_id to the database service ---
        self.db.create_state_change_and_link_events(
            asset_id=asset_id,
            event_type=new_state,
            timestamp=timestamp,
            log_bundle_hash=log_bundle_hash,
            on_chain_tx_id=on_chain_tx_id,
            event_ids_to_link=event_ids_to_link,
            new_asset_status=new_asset_status,
            final_sensor_id=final_sensor_id,
        )


class AnomalyProcessor:
    """
    Analyzes the current state of assets to find time-based anomalies.
    """

    def __init__(self, db_service: DatabaseService, bc_service: BlockchainService):
        self.db = db_service
        self.bc = bc_service
        self.transit_rules = config.TRANSIT_ANOMALY_RULES

    async def process_anomalies(self, assets: List[Dict]):
        """Checks for assets in transient state for too long. Now asynchronous."""
        for asset in assets:
            status = asset["current_status"]
            if status in ("IN_TRANSIT_OUT", "IN_TRANSIT_IN"):
                last_ts_str = asset.get("last_state_change_ts")
                if not last_ts_str:
                    continue

                last_ts = datetime.fromisoformat(last_ts_str)
                duration = datetime.now(last_ts.tzinfo) - last_ts

                max_duration = timedelta(
                    minutes=self.transit_rules["max_duration_minutes"]
                )

                if duration > max_duration:
                    print(f"ANOMALY: Asset {asset['id']} has exceeded transit time!")
                    await self._trigger_anomaly_state_change(
                        asset, "Transit Duration Exceeded"
                    )

    async def _trigger_anomaly_state_change(self, asset: Dict, reason: str):
        """Orchestrates creation of a SECURITY_BREACH state change. Now asynchronous."""
        asset_id = asset["id"]
        timestamp = datetime.now()
        new_state = "SECURITY_BREACH"

        # Create a deterministic hash for the anomaly event
        log_bundle_hash_input = (
            json.dumps(asset, default=str) + str(timestamp)
        ).encode()
        log_bundle_hash = hashlib.sha256(log_bundle_hash_input).hexdigest()

        on_chain_tx_id = await self.bc.record_state_change(
            asset_id=asset_id,
            event_type=new_state,
            log_bundle_hash=log_bundle_hash,
            timestamp=timestamp,
        )

        if not on_chain_tx_id:
            print(
                f"ERROR: Failed to get on-chain TX ID for ANOMALY on asset {asset_id}. Aborting DB commit."
            )
            return

        new_asset_status = config.NEXT_ASSET_STATUS_MAP[new_state]

        # Note: Anomalies don't link to prior events, as they are triggered by a lack of events.
        self.db.create_state_change_and_link_events(
            asset_id=asset_id,
            event_type=new_state,
            timestamp=timestamp,
            log_bundle_hash=log_bundle_hash,
            on_chain_tx_id=on_chain_tx_id,
            event_ids_to_link=[],
            new_asset_status=new_asset_status,
            # final_sensor_id=None,  # Anomalies don't have a sensor event
        )
