# aegis-daemon/check_balance.py
from blockfrost import BlockFrostApi, ApiError

# --- Configuration ---
# IMPORTANT: This must match the Project ID in your config.py
BLOCKFROST_PROJECT_ID = "previewFXX4wEluOaqmPbMQSe57LVsXoRXb0koP"

# The address you want to check.
WALLET_ADDRESS = "addr_test1vq47cckww94s4hv76yyeegem2n4ya4x03a0vssys92aqdlgk9c0l3"


def get_balance(address: str):
    """
    Connects to the Blockfrost API to fetch the balance of a Cardano address
    using a simple, synchronous method.
    """
    print(f"Querying balance for address: {address}...")
    try:
        # Initialize the SYNCHRONOUS Blockfrost API client
        api = BlockFrostApi(
            project_id=BLOCKFROST_PROJECT_ID,
            base_url="https://cardano-preview.blockfrost.io/api",
        )

        # Fetch the address details from the blockchain (no 'await' needed)
        address_info = api.address(address)

        # The amount is returned in a list. We need to find the entry for 'lovelace'.
        lovelace_balance = 0
        for amount in address_info.amount:
            if amount.unit == "lovelace":
                lovelace_balance = int(amount.quantity)
                break

        # Convert Lovelace to ADA (1 ADA = 1,000,000 Lovelace)
        ada_balance = lovelace_balance / 1_000_000

        print("\n" + "=" * 30)
        print("✅ Balance Found!")
        print(f"  -> ADA: {ada_balance:,.6f}")
        print(f"  -> Lovelace: {lovelace_balance:,}")
        print("=" * 30)

    except ApiError as e:
        if e.status_code == 404:
            print(f"\nERROR: Address not found on the blockchain.")
            print("This usually means it has not received any transactions yet.")
        else:
            print(f"\nERROR: An API error occurred: {e}")
    except Exception as e:
        print(f"\nERROR: A general error occurred: {e}")


if __name__ == "__main__":
    if WALLET_ADDRESS == "paste_your_address_here":
        print(
            "Please edit the script and replace 'paste_your_address_here' with your actual wallet address."
        )
    else:
        get_balance(WALLET_ADDRESS)
