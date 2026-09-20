import json
import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RPC_URL = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("ETH_PRIVATE_KEY", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")

ABI_PATH = BASE_DIR / "artifacts" / "contracts" / "PatientEHR.sol" / "PatientEHR.json"

if not PRIVATE_KEY:
    raise RuntimeError("ETH_PRIVATE_KEY is missing. Copy .env.example to .env and set it.")
if not CONTRACT_ADDRESS:
    raise RuntimeError("CONTRACT_ADDRESS is missing. Deploy the Solidity contract first.")
if not ABI_PATH.exists():
    raise RuntimeError("Contract ABI not found. Run: npm run compile")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"Cannot connect to Ethereum RPC at {RPC_URL}")

account = w3.eth.account.from_key(PRIVATE_KEY)

with open(ABI_PATH, "r", encoding="utf-8") as f:
    ABI = json.load(f)["abi"]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=ABI,
)


def _send(function):
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = w3.eth.gas_price

    tx = function.build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "gas": 700000,
        "gasPrice": gas_price,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        raise RuntimeError("Blockchain transaction reverted")

    return receipt


def create_record(record_id, patient_id, doctor_id, title, record_hash_hex):
    record_hash = bytes.fromhex(record_hash_hex)

    receipt = _send(
        contract.functions.createRecord(
            record_id,
            patient_id,
            doctor_id,
            title,
            record_hash,
        )
    )

    return receipt


def grant_access(patient_id, doctor_id, record_id, duration_seconds):
    """
    The Streamlit/backend layer supplies duration in seconds.
    The Solidity contract expects durationHours, so convert seconds
    to hours before sending the transaction.

    For the UI's usual values (24 hours, 48 hours, etc.) this is exact.
    """
    duration_seconds = int(duration_seconds)

    if duration_seconds <= 0:
        raise ValueError("Access duration must be greater than 0.")

    # Convert seconds to hours for the Solidity contract.
    # Round up so a positive duration is never accidentally reduced to 0.
    duration_hours = (duration_seconds + 3599) // 3600

    receipt = _send(
        contract.functions.grantAccess(
            patient_id,
            doctor_id,
            record_id,
            duration_hours,
        )
    )

    return receipt


def revoke_access(patient_id, doctor_id, record_id):
    receipt = _send(
        contract.functions.revokeAccess(
            patient_id,
            doctor_id,
            record_id,
        )
    )

    return receipt


def check_permission(patient_id, doctor_id, record_id):
    """
    PatientEHR.checkPermission() returns only a bool.
    Return (allowed, valid_until) here so the Flask layer can
    keep using the same two-value interface.
    """
    allowed = contract.functions.checkPermission(
        patient_id,
        doctor_id,
        record_id,
    ).call()

    if not allowed:
        return False, 0

    # The contract does not expose validUntil directly, so the
    # current Solidity interface can only reliably return the
    # authorization result. Use 0 for the unavailable timestamp.
    return True, 0


def get_record(record_id):
    return contract.functions.getRecord(record_id).call()


def get_block_number():
    return w3.eth.block_number


def get_record_count():
    return contract.functions.getRecordCount().call()


def get_record_by_index(index):
    return contract.functions.getRecordByIndex(index).call()


def tx_hash(receipt):
    return receipt.transactionHash.hex()


def block_number(receipt):
    return receipt.blockNumber


def explorer_data():
    count = get_record_count()
    records = []

    for i in range(count):
        r = get_record_by_index(i)

        records.append({
            "record_id": r[0],
            "patient_id": r[1],
            "doctor_id": r[2],
            "title": r[3],
            "record_hash": "0x" + bytes(r[4]).hex(),
            "created_at": r[5],
            "exists": r[6],
        })

    return records

def _to_hex(value):
    """Convert Web3/HexBytes/bytes values to a JSON-friendly hex string."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    if hasattr(value, "hex"):
        try:
            text = value.hex()
            if isinstance(text, str):
                return text if text.startswith("0x") else "0x" + text
        except Exception:
            pass
    return str(value)


def get_block_details(number):
    """Return one Ethereum block with transaction-level details."""
    number = int(number)
    if number < 0 or number > w3.eth.block_number:
        raise ValueError("Block number is outside the current chain range.")

    block = w3.eth.get_block(number, full_transactions=True)

    transactions = []
    for tx in block.transactions:
        tx_hash_value = _to_hex(tx.get("hash"))
        receipt = w3.eth.get_transaction_receipt(tx["hash"])
        transactions.append({
            "hash": tx_hash_value,
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value": str(tx.get("value", 0)),
            "nonce": int(tx.get("nonce", 0)),
            "gas": int(tx.get("gas", 0)),
            "gas_price": str(tx.get("gasPrice", tx.get("maxFeePerGas", 0))),
            "input": _to_hex(tx.get("input")),
            "status": int(receipt.get("status", 0)),
            "gas_used": int(receipt.get("gasUsed", 0)),
            "contract_address": receipt.get("contractAddress"),
        })

    return {
        "number": int(block["number"]),
        "hash": _to_hex(block["hash"]),
        "parent_hash": _to_hex(block["parentHash"]),
        "timestamp": int(block["timestamp"]),
        "miner": block.get("miner"),
        "gas_limit": int(block.get("gasLimit", 0)),
        "gas_used": int(block.get("gasUsed", 0)),
        "base_fee_per_gas": str(block.get("baseFeePerGas", 0)),
        "difficulty": str(block.get("difficulty", 0)),
        "nonce": _to_hex(block.get("nonce")),
        "size": int(block.get("size", 0)) if block.get("size") is not None else 0,
        "transaction_count": len(block.transactions),
        "transactions": transactions,
    }


def explorer_blocks():
    """Return a compact summary for every block currently on the chain."""
    latest = w3.eth.block_number
    blocks = []
    for number in range(latest + 1):
        block = w3.eth.get_block(number, full_transactions=False)
        blocks.append({
            "number": int(block["number"]),
            "hash": _to_hex(block["hash"]),
            "parent_hash": _to_hex(block["parentHash"]),
            "timestamp": int(block["timestamp"]),
            "miner": block.get("miner"),
            "gas_used": int(block.get("gasUsed", 0)),
            "gas_limit": int(block.get("gasLimit", 0)),
            "transaction_count": len(block.transactions),
        })
    return blocks
