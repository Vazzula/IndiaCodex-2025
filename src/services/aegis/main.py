import os
import time
import traceback
import asyncio

from src.services.aegis import config
from src.services.aegis.database import DatabaseService
from src.services.aegis.blockchain_service import BlockchainService
from src.services.aegis.processors import EventProcessor, AnomalyProcessor
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


class Daemon:
    def __init__(self):
        print("Initializing Aegis State Machine Daemon...")
        self.db_service = DatabaseService()
        self.bc_service = BlockchainService(
            base_url=config.CARDANO_BASE_URL,
            project_id=config.BLOCKFROST_PROJECT_ID,
            payment_skey_path=config.WALLET_SKEY_PATH,
            payment_vkey_path=config.WALLET_VKEY_PATH,
            dry_run=True,  # SAFE TESTING MODE: Set to False to send real transactions
        )
        self.event_processor = EventProcessor(self.db_service, self.bc_service)
        self.anomaly_processor = AnomalyProcessor(self.db_service, self.bc_service)
        self.running = True

    async def run_cycle(self):
        """Executes a single monitoring and processing cycle."""
        print(f"\n--- Starting new cycle at {time.ctime()} ---")

        active_assets = self.db_service.get_active_assets_state()
        unprocessed_events = self.db_service.get_unprocessed_tracking_events()

        await self.event_processor.process_events(active_assets, unprocessed_events)
        await self.anomaly_processor.process_anomalies(active_assets)

        print("--- Cycle finished ---")

    async def start(self):
        """Starts the main daemon loop."""
        print("Daemon started. Press Ctrl+C to stop.")
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(config.CYCLE_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                traceback.print_exc()
                await asyncio.sleep(config.CYCLE_INTERVAL_SECONDS * 2)

    def stop(self):
        """Stops the daemon gracefully."""
        print("\nStopping daemon...")
        self.running = False
        print("Daemon stopped.")


async def main():
    daemon = Daemon()
    await daemon.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDaemon terminated by user.")
