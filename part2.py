import os
import sys
import json
from typing import Any, Dict

from web3 import Web3


EIP1967_LABEL = "eip1967.proxy.implementation"
ZERO_ADDR = Web3.to_checksum_address("0x" + "0" * 40)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing env var: {name}. Example: export {name}=https://...")
    return value


def eip1967_impl_slot(w3: Web3) -> str:
    # bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)
    h = w3.keccak(text=EIP1967_LABEL)
    slot_int = int.from_bytes(h, "big") - 1
    return Web3.to_hex(slot_int.to_bytes(32, "big"))


def impl_from_slot(raw32: bytes) -> str:
    #last 20 bytes are the address
    if not raw32 or len(raw32) != 32:
        return ZERO_ADDR
    return Web3.to_checksum_address("0x" + raw32[-20:].hex())


def read_impl_at_block(w3: Web3, proxy: str, block_number: int) -> str:
    slot = eip1967_impl_slot(w3)
    raw = w3.eth.get_storage_at(proxy, slot, block_identifier=block_number)
    return impl_from_slot(raw)


def code_keccak(w3: Web3, address: str, block_number: int) -> str:
    code_bytes = w3.eth.get_code(address, block_identifier=block_number)
    return Web3.to_hex(w3.keccak(code_bytes))


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python part2.py <tx_hash> <proxy_address>")
        sys.exit(1)

    tx_hash = sys.argv[1].strip()
    proxy = Web3.to_checksum_address(sys.argv[2].strip())

    rpc_url = require_env("ETH_RPC_URL")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("ERROR: failed to connect to RPC (check ETH_RPC_URL).")
        sys.exit(1)

    #sanity checks
    proxy_code = w3.eth.get_code(proxy)
    if proxy_code in (b"", b"\x00"):
        print("ERROR: proxy address has no contract code.")
        sys.exit(1)

    receipt = w3.eth.get_transaction_receipt(tx_hash)
    block_number = int(receipt.get("blockNumber", 0))
    if block_number <= 0:
        print("ERROR: invalid block number in receipt.")
        sys.exit(1)
    if block_number == 0:
        print("ERROR: block_number is 0; cannot query block_number-1.")
        sys.exit(1)

    #compare impl slot
    impl_before = read_impl_at_block(w3, proxy, block_number - 1)
    impl_after = read_impl_at_block(w3, proxy, block_number)

    upgraded = impl_before.lower() != impl_after.lower()

    output: Dict[str, Any] = {"upgraded": upgraded}

    if upgraded:
        # more sanity: impl address should not be zero and should have code
        if impl_after == ZERO_ADDR:
            print("ERROR: implementation slot changed to zero address (unexpected).")
            sys.exit(1)

        impl_code = w3.eth.get_code(impl_after, block_identifier=block_number)
        if impl_code in (b"", b"\x00"):
            print("ERROR: new implementation address has no contract code.")
            sys.exit(1)

        # required output fields
        output["new_implementation_address"] = impl_after
        output["new_implementation_bytecode"] = w3.to_hex(impl_code)

        # if bytecode is equal, still upgraded
        code_before_hash = code_keccak(w3, impl_before, block_number)
        code_after_hash = code_keccak(w3, impl_after, block_number)
        output["bytecode_changed"] = (code_before_hash.lower() != code_after_hash.lower())

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
