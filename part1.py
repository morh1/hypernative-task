import os
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput

PAIR_ABI = [
    {"type": "function", "name": "token0", "stateMutability": "view", "inputs": [], "outputs": [{"type": "address"}]},
    {"type": "function", "name": "token1", "stateMutability": "view", "inputs": [], "outputs": [{"type": "address"}]},
]

ERC20_ABI = [
    {
        "type": "function",
        "name": "balanceOf",
        "stateMutability": "view",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "decimals",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint8"}],
    },
    {
        "type": "function",
        "name": "symbol",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "string"}],
    },
]


def _try(call, default=None):
    try:
        return call()
    except Exception:
        return default


def get_web3():

   #Connect to Ethereum node using environment variable.
    rpc_url = os.environ["ETH_RPC_URL"]
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError("RPC connection failed. Check ETH_RPC_URL or local node.")
    return w3


def fetch_uniswap_v2_pool_balances(pair_address: str):

    w3 = get_web3()
    pair = Web3.to_checksum_address(pair_address)

    #sanity check
    if w3.eth.get_code(pair) in (b"", b"\x00"):
        raise ValueError(f"No contract deployed at {pair}")

    pair_contract = w3.eth.contract(address=pair, abi=PAIR_ABI)

    try:
        token0 = Web3.to_checksum_address(pair_contract.functions.token0().call())
        token1 = Web3.to_checksum_address(pair_contract.functions.token1().call())
    except BadFunctionCallOutput as e:
        raise ValueError(f"{pair} doesn't behave like a UniswapV2Pair") from e

    t0 = w3.eth.contract(address=token0, abi=ERC20_ABI)
    t1 = w3.eth.contract(address=token1, abi=ERC20_ABI)

    #token balances in the pool (raw)
    bal0_raw = int(t0.functions.balanceOf(pair).call())
    bal1_raw = int(t1.functions.balanceOf(pair).call())

    #symbol metadata
    sym0 = _try(lambda: t0.functions.symbol().call())
    sym1 = _try(lambda: t1.functions.symbol().call())
    dec0 = _try(lambda: t0.functions.decimals().call())
    dec1 = _try(lambda: t1.functions.decimals().call())

    out = {
        "pair": pair,
        "token0": {"address": token0, "symbol": sym0, "balance_raw": bal0_raw},
        "token1": {"address": token1, "symbol": sym1, "balance_raw": bal1_raw},
    }

    if dec0 is not None:
        out["token0"]["balance"] = bal0_raw / (10 ** dec0)
    if dec1 is not None:
        out["token1"]["balance"] = bal1_raw / (10 ** dec1)

    return out


if __name__ == "__main__":

    pairs = [
        "0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11",
        "0x255Ecb43d40e686Ca0914348fc6b012e0bE14DD0",
    ]

    for p in pairs:
        info = fetch_uniswap_v2_pool_balances(p)
        print("\nPair:", info["pair"])
        print("token0:", info["token0"])
        print("token1:", info["token1"])
