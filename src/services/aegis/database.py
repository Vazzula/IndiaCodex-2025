import os
from contextlib import contextmanager
from typing import List, Dict, Any, Generator
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session, subqueryload
from sqlalchemy.exc import SQLAlchemyError

from src.database.entities.assets import Asset, AssetStatusEnum
from src.database.entities.asset_tracking import AssetTracking
from src.database.entities.state_change import StateChange, StateChangeEventEnum


class DatabaseService:
    def __init__(self):
        db_url = os.getenv("DATABASE_URL")
        self.engine = create_engine(db_url)
        self.SessionFactory = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        print("Database service initialized with SQLAlchemy.")

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            print(f"DB Error: Transaction failed and rolled back. Error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_active_assets_state(self) -> List[Dict[str, Any]]:
        """
        Fetches the current state of all assets not yet released, including the
        timestamp of their most recent state change.
        """
        print("DB: Fetching active asset states via SQLAlchemy...")
        with self.session_scope() as session:
            # Create a subquery to find the latest timestamp for each asset
            latest_sc_subq = (
                session.query(
                    StateChange.asset_id,
                    func.max(StateChange.timestamp).label("last_state_change_ts"),
                )
                .group_by(StateChange.asset_id)
                .subquery()
            )

            # Join the Asset table with the subquery
            results = (
                session.query(Asset, latest_sc_subq.c.last_state_change_ts)
                .outerjoin(latest_sc_subq, Asset.id == latest_sc_subq.c.asset_id)
                .filter(Asset.current_status != AssetStatusEnum.RELEASED)
                .all()
            )

            # Format the results into the dictionary structure the processors expect
            asset_states = [
                {
                    "id": asset.id,
                    "current_status": asset.current_status.value,  # Return the string value of the enum
                    "last_state_change_ts": ts.isoformat() if ts else None,
                }
                for asset, ts in results
            ]
            return asset_states

    def get_unprocessed_tracking_events(self) -> List[Dict[str, Any]]:
        """
        Fetches all asset_tracking events that have not been linked to a state change.
        """
        print("DB: Fetching unprocessed tracking events via SQLAlchemy...")
        with self.session_scope() as session:
            events = (
                session.query(AssetTracking)
                .filter(AssetTracking.state_change_id.is_(None))
                .order_by(AssetTracking.timestamp.asc())
                .all()
            )
            # Convert ORM objects to dictionaries
            return [
                {
                    "id": event.id,
                    "asset_id": event.asset_id,
                    "event_type": event.event_type,
                    "details": event.details,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in events
            ]

    def create_state_change_and_link_events(
        self,
        asset_id: str,
        event_type: str,
        timestamp: Any,
        log_bundle_hash: str,
        on_chain_tx_id: str,
        event_ids_to_link: List[int],
        new_asset_status: str,
    ):
        """
        A transactional function using SQLAlchemy to create a state change,
        update tracking events, and update the asset's status.
        """
        print("\n" + "=" * 50)
        print("DB: SQLAlchemy Transaction Start - Creating New State Change")

        with self.session_scope() as session:
            # 1. Fetch the parent asset
            asset_to_update = session.query(Asset).filter(Asset.id == asset_id).one()

            # 2. Create the new StateChange record
            new_state_change = StateChange(
                asset_id=asset_id,
                event_type=StateChangeEventEnum(event_type),
                timestamp=timestamp,
                log_bundle_hash=log_bundle_hash,
                on_chain_tx_id=on_chain_tx_id,
            )
            session.add(new_state_change)

            # 3. Find and link the asset_tracking records
            if event_ids_to_link:
                events_to_link = (
                    session.query(AssetTracking)
                    .filter(AssetTracking.id.in_(event_ids_to_link))
                    .all()
                )
                for event in events_to_link:
                    event.state_change = new_state_change

            # 4. Update the asset's current_status
            asset_to_update.current_status = AssetStatusEnum(new_asset_status)

            print(f"  - Committing state change '{event_type}' for asset {asset_id}")
            print("=" * 50 + "\n")

        print("DB: SQLAlchemy transaction committed successfully.")
