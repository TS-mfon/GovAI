"""Deploy the GovAI GenLayer Intelligent Contract (the AI brain) to GenLayer.

Reads the contract source, deploys it to the configured GenLayer network, waits for
consensus FINALIZED, extracts the deployed contract address from the transaction
receipt, and writes it to `backend/.env` as `GENLAYER_CONTRACT`.

Requires:
  GENLAYER_ACCOUNT  - private key (0x-hex) of a *funded* account on the target network
  GENLAYER_NETWORK  - studionet (default) | testnet_asimov | testnet_bradbury | localnet

For studionet, fund the account via the GenLayer studionet faucet (studio.genlayer.com)
BEFORE running this script. `client.fund_account()` only works on localnet.

Usage:
  cd deploy
  GENLAYER_NETWORK=studionet python deploy_genlayer.py
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from eth_account import Account

from genlayer_py.chains import (
    localnet,
    studionet,
    testnet_asimov,
    testnet_bradbury,
)
from genlayer_py.client import create_client
from genlayer_py.types import TransactionStatus

CONTRACT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "contracts", "genlayer", "govai_decision.py"
)
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")

_CHAIN_MAP = {
    "localnet": localnet,
    "studionet": studionet,
    "testnet": testnet_asimov,
    "testnet_asimov": testnet_asimov,
    "testnet_bradbury": testnet_bradbury,
    "bradbury": testnet_bradbury,
}


def _extract_contract_address(receipt: dict) -> str | None:
    """Pull the deployed contract address out of a GenLayer deploy receipt.

    On testnet the new contract address is in `recipient`; on localnet it is in
    `to_address`. GenLayer also nests `contract_address` under `decoded_input_data`.
    """
    for key in ("recipient", "to_address", "contract_address"):
        v = receipt.get(key)
        if isinstance(v, str) and v.startswith("0x") and v != "0x" + "0" * 40:
            return v
    decoded = receipt.get("decoded_input_data") or receipt.get("input_data")
    if isinstance(decoded, dict):
        v = decoded.get("contract_address")
        if isinstance(v, str) and v.startswith("0x") and v != "0x" + "0" * 40:
            return v
    return None


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    pk = os.environ.get("GENLAYER_ACCOUNT")
    network = os.environ.get("GENLAYER_NETWORK", "studionet").lower()
    if not pk or pk == "0x" + "0" * 40:
        print(
            "ERROR: GENLAYER_ACCOUNT must be a funded private key (0x-hex).",
            file=sys.stderr,
        )
        return 1
    chain = _CHAIN_MAP.get(network, studionet)
    account = Account.from_key(pk)
    client = create_client(chain=chain, account=account)

    code = open(CONTRACT_PATH, "r", encoding="utf-8").read()
    print(f"Deploying GovAI decision contract to GenLayer '{network}' ...")
    print(f"  source : {CONTRACT_PATH}  ({len(code)} bytes)")
    tx_hash = client.deploy_contract(code=code, account=account)
    print(f"  tx_hash: {tx_hash}")
    print("  waiting for consensus FINALIZED (this can take ~1 minute)...")
    receipt = client.wait_for_transaction_receipt(
        tx_hash, status=TransactionStatus.FINALIZED
    )
    addr = _extract_contract_address(receipt)

    print("Deployed.")
    print(f"  contract_address = {addr}")
    if not addr:
        print(
            "WARNING: could not extract contract_address from receipt. Full receipt:",
            file=sys.stderr,
        )
        print(receipt, file=sys.stderr)
        return 2

    # Persist GENLAYER_CONTRACT into backend/.env
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        replaced = False
        out: list[str] = []
        for ln in lines:
            if ln.startswith("GENLAYER_CONTRACT="):
                out.append(f"GENLAYER_CONTRACT={addr}\n")
                replaced = True
            else:
                out.append(ln)
        if not replaced:
            out.append(f"GENLAYER_CONTRACT={addr}\n")
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(out)
        print(f"  updated GENLAYER_CONTRACT in {ENV_PATH}")
    except Exception as e:
        print(f"WARNING: could not auto-update {ENV_PATH}: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())