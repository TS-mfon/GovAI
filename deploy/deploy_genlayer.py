"""Deploy the GovAI GenLayer Intelligent Contract (the AI brain) to GenLayer testnet.

Requires the genlayer-py SDK and a configured GenLayer account/network.
Run: GENLAYER_ACCOUNT=0x... GENLAYER_NETWORK=testnet python deploy_genlayer.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "contracts", "genlayer"))

from genlayer_py import Client
from genlayer_py.types import TransactionStatus

CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "..", "contracts", "genlayer", "govai_decision.py")


def main():
    account = os.environ["GENLAYER_ACCOUNT"]
    network = os.environ.get("GENLAYER_NETWORK", "testnet")
    client = Client(network=network)
    code = open(CONTRACT_PATH).read()
    tx = client.deploy_contract(code=code, account=account)
    receipt = client.wait_for_transaction_receipt(tx, status=TransactionStatus.FINALIZED)
    print("Deployed GovAI decision contract. Receipt:")
    print(receipt)


if __name__ == "__main__":
    main()
