"""Relayer: the GovAI bridge between GenLayer (AI) and X Layer (governance).

Flow:
  X Layer proposal submitted (stage=Submitted)
    -> relayer calls GenLayer review_proposal (comparative consensus)
    -> GenLayer returns verdict + scores
    -> relayer flattens into the AIReport struct and calls X Layer submitAIReport
    -> if the DAO's token is on another chain, relayer verifies holdings via the
       Etherscan-compatible API, builds a Merkle snapshot, and calls setVotingSnapshot
    -> X Layer opens Voting (or Rejected)
"""
from typing import Optional
from chain import XLayerClient
from genlayer_client import GovAIClient
from token_verify import ChainExplorer, build_snapshot


def flatten_report(genlayer_report: dict) -> dict:
    """GenLayer returns nested {alignment, scores}; X Layer wants a flat AIReport."""
    a = genlayer_report.get("alignment", {})
    s = genlayer_report.get("scores", {})
    return {
        "passed": bool(genlayer_report.get("passed", False)),
        "reason": str(genlayer_report.get("reason", "")),
        "intentClarity": int(s.get("intent_clarity", 0)),
        "benefitScore": int(s.get("benefit_score", 0)),
        "riskScore": int(s.get("risk_score", 0)),
        "selfDealing": bool(s.get("self_dealing_flag", False)),
        "malicious": bool(s.get("malicious_flag", False)),
        "confidence": int(float(a.get("confidence", 0)) * 100),
    }


def run_ai_review(
    x: XLayerClient,
    g: GovAIClient,
    proposal_id: int,
    proposal_cid: str,
    constitution_cid: str,
    supported_chains: dict[int, dict],
    xlayer_chain_id: int,
    member_count: Optional[int] = None,
) -> dict:
    prop = x.get_proposal(proposal_id)
    dao = x.get_dao(prop["daoId"])

    # 1) GenLayer comparative-consensus review
    report = g.review(str(dao["name"]), str(proposal_id), constitution_cid, proposal_cid)
    flat = flatten_report(report)

    # 2) Deliver verdict to X Layer
    x.submit_ai_report(proposal_id, flat)

    # 3) Voting-weight snapshot
    token = dao["token"]
    chain_id = int(dao["chainId"])
    if token == "0x0000000000000000000000000000000000000000":
        # No token: 1 address = 1 vote. total_weight = known members (quorum basis).
        total_weight = max(member_count or 1, 1)
        x.set_voting_snapshot(proposal_id, "0x" + "0" * 64, total_weight)
    elif chain_id == xlayer_chain_id:
        # Native X Layer token: weight read on-chain via balanceOf; quorum = total supply.
        explorer = ChainExplorer(supported_chains[chain_id]["rpc"])
        total_weight = explorer.total_supply(token, explorer.w3.eth.block_number)
        x.set_voting_snapshot(proposal_id, "0x" + "0" * 64, total_weight)
    else:
        # External EVM token: verify via Etherscan API, Merkle-root the weights.
        info = supported_chains.get(chain_id)
        if not info:
            raise RuntimeError(f"chain {chain_id} not supported for token verification")
        explorer = ChainExplorer(info["rpc"], info.get("api"), info.get("key"))
        block = explorer.w3.eth.block_number
        root, total_weight, _entries = build_snapshot(token, explorer, block)
        x.set_voting_snapshot(proposal_id, root, total_weight)

    return flat
