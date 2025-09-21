import asyncio
import os
from datetime import datetime
import hashlib
from dotenv import find_dotenv, load_dotenv

# Important: This assumes your test script is in the project root,
# and your service is in src/services/aegis/
from src.services.aegis.blockchain_service import BlockchainService
from src.services.aegis import config

# Load environment variables from .env file
load_dotenv(find_dotenv())


async def main():
    """
    Initializes the BlockchainService and attempts to send a single,
    hard-coded transaction to the Cardano network to test the connection.
    """
    print("--- Starting Standalone Blockchain Service Test ---")

    # --- 1. Hard-coded Test Data ---
    # This data mimics what the EventProcessor would normally provide.
    test_asset_id = (
        "a2b3cc56-b8e3-46d8-bcf5-d8f62cc5697a"  # Using the ruby's ID for consistency
    )
    test_event_type = "VAULT_EXIT_TEST"
    test_timestamp = datetime.now()
    # Create a simple, repeatable hash for the test
    test_log_bundle_hash = hashlib.sha256(
        f"{test_asset_id}{test_timestamp}".encode()
    ).hexdigest()

    print(f"\nAttempting to record a test event on-chain:")
    print(f"  - Asset ID: {test_asset_id}")
    print(f"  - Event Type: {test_event_type}")
    print(f"  - Timestamp: {test_timestamp.isoformat()}")
    print(f"  - Log Hash: {test_log_bundle_hash}")

    try:
        # --- 2. Initialize the Blockchain Service ---
        # It will pull its configuration from your .env and config.py files
        print("\nInitializing BlockchainService...")
        bc_service = BlockchainService(
            base_url=config.CARDANO_BASE_URL,
            project_id=config.BLOCKFROST_PROJECT_ID,
            payment_skey_path=config.WALLET_SKEY_PATH,
            payment_vkey_path=config.WALLET_VKEY_PATH,
        )

        # --- 3. Call the core function ---
        tx_id = await bc_service.record_state_change(
            asset_id=test_asset_id,
            event_type=test_event_type,
            log_bundle_hash=test_log_bundle_hash,
            timestamp=test_timestamp,
        )

        # --- 4. Report the result ---
        if tx_id:
            print("\n" + "=" * 50)
            print("  ✅ SUCCESS! Transaction submitted and confirmed.")
            print(f"  On-Chain Transaction ID: {tx_id}")
            print(f"  You can view it on a Cardano explorer for the Preview network.")
            print("=" * 50)
        else:
            print("\n" + "!" * 50)
            print("  ❌ FAILURE. The service did not return a transaction ID.")
            print(
                "  This likely means an error occurred during transaction building or submission."
            )
            print(
                "  Check the logs above for specific error messages from Blockfrost or PyCardano."
            )
            print("!" * 50)

    except Exception as e:
        print(f"\n--- An unexpected FATAL error occurred ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        # print("\nCommon causes for failure:")
        # print("  - Incorrect file path for wallet keys in config.py.")
        # print("  - Incorrect Blockfrost Project ID or Base URL in .env.")
        # print(
        #     "  - The wallet at the specified address has insufficient funds (needs ~2 ADA)."
        # )
        # print("  - Network connectivity issues.")


if __name__ == "__main__":
    # Ensure you have installed the necessary dependencies for the service:
    # pip install pycardano blockfrost-python
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
