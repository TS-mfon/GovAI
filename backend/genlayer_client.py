"""GenLayer client — drives the GovAI Intelligent Contract (the AI brain).

Wraps genlayer-py 0.18.x: submits a proposal for review (comparative consensus on
GenLayer) and reads back the verdict via the on-chain `get_review` view.

The GenLayer Intelligent Contract (`contracts/genlayer/govai_decision.py`) stores a
report dict on `get_review` with this shape:
    {
      "dao_id": str, "proposal_id": str,
      "passed": bool, "reason": str,
      "alignment": {"aligned": bool, "confidence": float, "conflicts": [...], ...},
      "scores":    {"intent_clarity": int, "benefit_score": int, "risk_score": int,
                    "self_dealing_flag": bool, "malicious_flag": bool, ...},
    }
`relayer.flatten_report()` maps that into the flat `AIReport` struct expected by the
X Layer `ProposalRegistry`.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount

from genlayer_py.chains import (
    localnet as _localnet,
    testnet_asimov as _testnet_asimov,
    testnet_bradbury as _testnet_bradbury,
    studionet as _studionet,
)
from genlayer_py.client import create_client
from genlayer_py.types import TransactionStatus


_NETWORK_TO_CHAIN = {
    "localnet": _localnet,
    "testnet": _testnet_asimov,   # default GenLayer testnet
    "testnet_asimov": _testnet_asimov,
    "testnet_bradbury": _testnet_bradbury,
    "bradbury": _testnet_bradbury,
    "studionet": _studionet,
    "studio": _studionet,
}


class GovAIClient:
    """Thin wrapper around `genlayer-py`'s GenLayerClient for the GovAI contract."""

    def __init__(
        self,
        contract_address: str,
        account: str,
        network: str = "testnet",
        endpoint: Optional[str] = None,
    ):
        if not contract_address or contract_address == "0x" + "0" * 40:
            raise ValueError(
                "GovAIClient: contract_address must be set "
                "(deploy the GenLayer intelligent contract first)."
            )
        chain = _NETWORK_TO_CHAIN.get(network.lower(), _testnet_asimov)
        # Allow GENLAYER_RPC_URL env override if no explicit endpoint.
        endpoint = endpoint or os.getenv("GENLAYER_RPC_URL")
        local_acct: Optional[LocalAccount] = None
        if account and account != "0x" + "0" * 40:
            try:
                local_acct = Account.from_key(account)
            except Exception as e:
                raise ValueError(
                    f"GovAIClient: invalid private key in GENLAYER_ACCOUNT: {e}"
                ) from e
        self.local_account = local_acct
        self.address = contract_address
        self.network = network
        self.client = create_client(chain=chain, endpoint=endpoint, account=local_acct)

    # ---- helpers ----
    def _require_signer(self) -> None:
        if self.local_account is None:
            raise RuntimeError(
                "GovAIClient: write op needs a signer — set GENLAYER_ACCOUNT to a "
                "funded private key (0x-prefixed hex)."
            )

    # ---- core flows ----
    def review(
        self,
        dao_id: str,
        proposal_id: str,
        constitution_cid: str,
        proposal_cid: str,
    ) -> dict[str, Any]:
        """Run the comparative-consensus AI review and return the stored report."""
        self._require_signer()
        tx = self.client.write_contract(
            self.address,
            "review_proposal",
            args=[dao_id, proposal_id, constitution_cid, proposal_cid],
            account=self.local_account,
        )
        self.client.wait_for_transaction_receipt(
            tx, status=TransactionStatus.FINALIZED
        )
        return self.client.read_contract(
            self.address, "get_review", args=[proposal_id]
        )

    def appeal(
        self,
        dao_id: str,
        proposal_id: str,
        constitution_cid: str,
        proposal_cid: str,
    ) -> dict[str, Any]:
        """Trigger a fresh comparative-consensus review via the appeal flow."""
        self._require_signer()
        tx = self.client.write_contract(
            self.address,
            "appeal",
            args=[dao_id, proposal_id, constitution_cid, proposal_cid],
            account=self.local_account,
        )
        self.client.wait_for_transaction_receipt(
            tx, status=TransactionStatus.FINALIZED
        )
        return self.client.read_contract(
            self.address, "get_review", args=[proposal_id]
        )

    def get_review(self, proposal_id: str) -> dict[str, Any]:
        return self.client.read_contract(
            self.address, "get_review", args=[proposal_id]
        )