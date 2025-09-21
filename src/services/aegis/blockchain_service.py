import json
from datetime import datetime
import time
import asyncio

from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Address,
    BlockFrostChainContext,
    PaymentSigningKey,
    PaymentVerificationKey,
    AuxiliaryData,
    Metadata,
    Network,
)
from pycardano.metadata import AlonzoMetadata
from blockfrost import ApiError

# --- Constants ---
METADATA_KEY = 1337


class BlockchainService:
    def __init__(
        self,
        base_url: str,
        project_id: str,
        payment_skey_path: str,
        payment_vkey_path: str,
        dry_run: bool = False,  # Add the dry_run flag
    ):
        """
        Initializes the BlockchainService with everything needed to interact with Cardano.
        """
        try:
            self.base_url = base_url
            self.project_id = project_id
            self.dry_run = dry_run
            self.network = (
                Network.TESTNET
                if "preview" in base_url or "preprod" in base_url
                else Network.MAINNET
            )

            self.payment_skey = PaymentSigningKey.load(payment_skey_path)
            self.payment_vkey = PaymentVerificationKey.load(payment_vkey_path)
            self.address = Address(self.payment_vkey.hash(), network=self.network)

            print(f"Blockchain service initialized for network: {self.network}")
            print(f"Wallet Address: {self.address}")
            if self.dry_run:
                print("\n" + "=" * 25)
                print("  BLOCKCHAIN DRY RUN MODE IS ACTIVE")
                print("  No real transactions will be sent.")
                print("=" * 25 + "\n")

        except Exception as e:
            print(f"FATAL: Could not initialize BlockchainService. Error: {e}")
            raise

    async def record_state_change(
        self, asset_id: str, event_type: str, log_bundle_hash: str, timestamp: datetime
    ) -> str:
        """
        Constructs, signs, and submits a Cardano transaction with state change data in its metadata.
        In dry_run mode, it simulates this process and returns a fake TX ID.
        """
        print(f"\nBLOCKCHAIN: Preparing to record state change on Cardano...")

        metadata_payload = {
            "asset_id": str(asset_id),
            "event": event_type,
            "log_hash": log_bundle_hash,
            "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
        }

        print(f"  - Metadata Payload: {json.dumps(metadata_payload)}")

        if self.dry_run:
            print("  - [DRY RUN] Skipping transaction build and submission.")
            fake_tx_id = f"dry_run_tx_{int(time.time())}"
            print(f"  - [DRY RUN] Returning fake TX ID: {fake_tx_id}")
            return fake_tx_id

        try:
            context = BlockFrostChainContext(self.project_id, base_url=self.base_url)

            auxiliary_data = AuxiliaryData(
                AlonzoMetadata(metadata=Metadata({METADATA_KEY: metadata_payload}))
            )

            builder = TransactionBuilder(context)
            builder.add_input_address(self.address)
            builder.auxiliary_data = auxiliary_data

            signed_tx = builder.build_and_sign(
                signing_keys=[self.payment_skey], change_address=self.address
            )

            print(f"  - Submitting transaction to Cardano network...")
            tx_hash = context.submit_tx(signed_tx.to_cbor())
            print(f"  - Transaction Submitted! Awaiting confirmation...")
            print(f"  - On-Chain TX ID: {tx_hash}")

            await self.wait_for_tx_confirmation(context, str(tx_hash))

            return str(tx_hash)

        except ApiError as e:
            print(f"BLOCKCHAIN ERROR: Blockfrost API error: {e}")
            return ""
        except Exception as e:
            print(f"BLOCKCHAIN ERROR: Failed to build or submit transaction: {e}")
            raise

    async def wait_for_tx_confirmation(
        self,
        context: BlockFrostChainContext,
        tx_hash: str,
        timeout: int = 300,
        interval: int = 15,
    ):
        """
        Waits for a transaction to be confirmed on the blockchain by repeatedly querying Blockfrost.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # --- FINAL FIX: Removed the incorrect 'await' ---
                # The .transaction() method is synchronous and returns a result directly.
                context.api.transaction(tx_hash)
                print(f"  - Transaction Confirmed on-chain: {tx_hash}")
                return
            except ApiError as e:
                if e.status_code == 404:
                    print("  - ...tx not yet confirmed, waiting...")
                    await asyncio.sleep(interval)
                else:
                    raise
        raise TimeoutError(
            f"Transaction {tx_hash} was not confirmed within {timeout} seconds."
        )
