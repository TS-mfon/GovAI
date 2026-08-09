"""X Layer (OKX L2) client — reads/writes GovAI governance contracts.

The voting chain is X Layer. This client relays DAO registration, proposal submission,
AI reports, voting snapshots, votes, and finalization. All writes are signed with the
relayer's key (configured in the GovAI backend, not by end users).
"""
import os
from typing import Optional
from web3 import Web3
from eth_utils import to_checksum_address

ZERO = "0x0000000000000000000000000000000000000000"

STAGE_NAMES = ["Submitted", "AIReview", "Voting", "Executed", "Defeated", "Rejected"]

REGISTRY_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "name", "type": "string"},
                    {"name": "mission", "type": "string"},
                    {"name": "constitutionHash", "type": "bytes32"},
                    {"name": "token", "type": "address"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "maxRisk", "type": "uint256"},
                    {"name": "minBenefit", "type": "uint256"},
                    {"name": "minConfidence", "type": "uint256"},
                    {"name": "votingDuration", "type": "uint256"},
                    {"name": "quorumBps", "type": "uint256"},
                    {"name": "delegationOn", "type": "bool"},
                ],
                "name": "cfg",
                "type": "tuple",
            }
        ],
        "name": "registerDAO",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "daoId", "type": "uint256"}],
        "name": "getDAO",
        "outputs": [
            {
                "components": [
                    {"name": "name", "type": "string"},
                    {"name": "mission", "type": "string"},
                    {"name": "constitutionHash", "type": "bytes32"},
                    {"name": "token", "type": "address"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "maxRisk", "type": "uint256"},
                    {"name": "minBenefit", "type": "uint256"},
                    {"name": "minConfidence", "type": "uint256"},
                    {"name": "votingDuration", "type": "uint256"},
                    {"name": "quorumBps", "type": "uint256"},
                    {"name": "delegationOn", "type": "bool"},
                    {"name": "owner", "type": "address"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

PROPOSAL_ABI = [
    {
        "inputs": [
            {"name": "daoId", "type": "uint256"},
            {"name": "proposalCid", "type": "bytes32"},
            {"name": "constitutionCid", "type": "bytes32"},
        ],
        "name": "submitProposal",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "proposalId", "type": "uint256"},
            {
                "components": [
                    {"name": "passed", "type": "bool"},
                    {"name": "reason", "type": "string"},
                    {"name": "intentClarity", "type": "uint8"},
                    {"name": "benefitScore", "type": "uint8"},
                    {"name": "riskScore", "type": "uint8"},
                    {"name": "selfDealing", "type": "bool"},
                    {"name": "malicious", "type": "bool"},
                    {"name": "confidence", "type": "uint8"},
                ],
                "name": "report",
                "type": "tuple",
            },
        ],
        "name": "submitAIReport",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "proposalId", "type": "uint256"},
            {"name": "root", "type": "bytes32"},
            {"name": "totalWeight", "type": "uint256"},
        ],
        "name": "setVotingSnapshot",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "proposalId", "type": "uint256"}],
        "name": "finalize",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "proposalId", "type": "uint256"}],
        "name": "getProposal",
        "outputs": [
            {
                "components": [
                    {"name": "daoId", "type": "uint256"},
                    {"name": "proposer", "type": "address"},
                    {"name": "proposalCid", "type": "bytes32"},
                    {"name": "constitutionCid", "type": "bytes32"},
                    {"name": "stage", "type": "uint8"},
                    {"name": "createdAt", "type": "uint256"},
                    {"name": "votingEndsAt", "type": "uint256"},
                    {"name": "totalWeight", "type": "uint256"},
                    {"name": "quorumBps", "type": "uint256"},
                    {
                        "components": [
                            {"name": "passed", "type": "bool"},
                            {"name": "reason", "type": "string"},
                            {"name": "intentClarity", "type": "uint8"},
                            {"name": "benefitScore", "type": "uint8"},
                            {"name": "riskScore", "type": "uint8"},
                            {"name": "selfDealing", "type": "bool"},
                            {"name": "malicious", "type": "bool"},
                            {"name": "confidence", "type": "uint8"},
                        ],
                        "name": "report",
                        "type": "tuple",
                    },
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

DELEGATION_ABI = [
    {
        "inputs": [
            {"name": "daoId", "type": "uint256"},
            {"name": "to", "type": "address"},
        ],
        "name": "delegate",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

VOTING_ABI = [
    {
        "inputs": [
            {"name": "proposalId", "type": "uint256"},
            {"name": "daoId", "type": "uint256"},
            {"name": "token", "type": "address"},
            {"name": "chainId", "type": "uint256"},
            {"name": "support", "type": "bool"},
            {"name": "claimedWeight", "type": "uint256"},
            {"name": "proof", "type": "bytes32[]"},
            {"name": "delegators", "type": "address[]"},
            {"name": "delegatorWeights", "type": "uint256[]"},
            {"name": "delegatorProofs", "type": "bytes32[][]"},
        ],
        "name": "castVote",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def _cid_bytes(cid: str) -> bytes:
    return Web3.keccak(text=cid)


class XLayerClient:
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        registry: str,
        proposal_registry: str,
        delegation: str,
        voting: str,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = self.w3.eth.account.from_key(private_key)
        self.registry = self.w3.eth.contract(address=to_checksum_address(registry), abi=REGISTRY_ABI)
        self.proposal = self.w3.eth.contract(address=to_checksum_address(proposal_registry), abi=PROPOSAL_ABI)
        self.delegation = self.w3.eth.contract(address=to_checksum_address(delegation), abi=DELEGATION_ABI)
        self.voting = self.w3.eth.contract(address=to_checksum_address(voting), abi=VOTING_ABI)

    def _send(self, fn):
        tx = fn.build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.w3.eth.chain_id,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    # ---- DAO ----
    def register_dao(self, cfg: dict) -> int:
        cfg = dict(cfg)
        cfg["constitutionHash"] = _cid_bytes(cfg["constitutionCid"])
        cfg["token"] = to_checksum_address(cfg.get("token", ZERO))
        receipt = self._send(self.registry.functions.registerDAO(cfg))
        # daoId is the new daoCount; read it back via event or return from receipt logs.
        return self.registry.functions.daoCount().call()

    def get_dao(self, dao_id: int) -> dict:
        c = self.registry.functions.getDAO(dao_id).call()
        keys = ["name", "mission", "constitutionHash", "token", "chainId", "maxRisk",
                "minBenefit", "minConfidence", "votingDuration", "quorumBps", "delegationOn", "owner"]
        return dict(zip(keys, c))

    # ---- Proposal ----
    def submit_proposal(self, dao_id: int, proposal_cid: str, constitution_cid: str) -> int:
        self._send(
            self.proposal.functions.submitProposal(
                dao_id, _cid_bytes(proposal_cid), _cid_bytes(constitution_cid)
            )
        )
        return self.proposal.functions.proposalCount().call()

    def get_proposal(self, proposal_id: int) -> dict:
        p = self.proposal.functions.getProposal(proposal_id).call()
        keys = ["daoId", "proposer", "proposalCid", "constitutionCid", "stage", "createdAt",
                "votingEndsAt", "totalWeight", "quorumBps", "report"]
        d = dict(zip(keys, p))
        d["stage"] = STAGE_NAMES[d["stage"]]
        r = d["report"]
        d["aiReport"] = {
            "passed": r[0], "reason": r[1], "intentClarity": r[2], "benefitScore": r[3],
            "riskScore": r[4], "selfDealing": r[5], "malicious": r[6], "confidence": r[7],
        }
        return d

    def submit_ai_report(self, proposal_id: int, report: dict) -> None:
        self._send(self.proposal.functions.submitAIReport(proposal_id, report))

    def set_voting_snapshot(self, proposal_id: int, root: str, total_weight: int) -> None:
        self._send(self.proposal.functions.setVotingSnapshot(proposal_id, bytes.fromhex(root[2:]), total_weight))

    def finalize(self, proposal_id: int) -> None:
        self._send(self.proposal.functions.finalize(proposal_id))

    # ---- Voting / delegation ----
    def cast_vote(
        self,
        proposal_id: int,
        dao_id: int,
        token: str,
        chain_id: int,
        support: bool,
        claimed_weight: int = 0,
        proof: Optional[list] = None,
        delegators: Optional[list] = None,
        delegator_weights: Optional[list] = None,
        delegator_proofs: Optional[list] = None,
    ) -> None:
        self._send(
            self.voting.functions.castVote(
                proposal_id, dao_id, to_checksum_address(token), chain_id, support,
                claimed_weight, proof or [], delegators or [], delegator_weights or [], delegator_proofs or [],
            )
        )

    def delegate(self, dao_id: int, to: str) -> None:
        self._send(self.delegation.functions.delegate(dao_id, to_checksum_address(to)))
