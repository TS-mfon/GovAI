"""GovAI backend API (FastAPI).

Exposes the cross-DAO governance surface: DAO onboarding, proposal submission, the
GenLayer-driven AI review (via the relayer), token-weighted voting, delegation, and the
cross-DAO proposal feed with AI summaries. Acts as the bridge between users, GenLayer
(AI), and X Layer (on-chain governance).
"""
import os
import json
import asyncio
import uuid
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ipfs import IPFSClient
from chain import XLayerClient
from genlayer_client import GovAIClient
from relayer import run_ai_review
from summarizer import summarize_batch
from models import AIReport

load_dotenv()

app = FastAPI(title="GovAI", version="0.1.0")

# CORS — allow the deployed frontend (Vercel) to call this API.
# FRONTEND_ORIGIN is a comma-separated allowlist; defaults to "*" for the demo.
_allowed_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ipfs = IPFSClient()

# In-memory mirrors (an indexer would back these with Postgres in production).
DAOS: dict[int, dict] = {}                       # daoId -> config + name
PROPOSALS: dict[int, dict] = {}                 # proposalId -> {daoId, title, body, cids}
PROPOSAL_CIDS: dict[int, tuple[str, str]] = {}  # proposalId -> (proposalCid, constitutionCid)
TASKS: dict[str, dict] = {}                     # taskId -> {status, result?, error?, proposalId}

# ---- request models ----
class RegisterDAO(BaseModel):
    name: str
    mission: str
    constitution: str  # raw text; pinned to IPFS
    token: str = "0x0000000000000000000000000000000000000000"
    chainId: int = 0
    maxRisk: int = 60
    minBenefit: int = 40
    minConfidence: int = 60
    votingDuration: int = 3 * 24 * 3600
    quorumBps: int = 4000
    delegationOn: bool = True


class SubmitProposal(BaseModel):
    daoId: int
    title: str
    body: str


class VoteBody(BaseModel):
    daoId: int
    token: str = "0x0000000000000000000000000000000000000000"
    chainId: int = 0
    support: bool
    claimedWeight: int = 0
    proof: list[str] = []
    delegators: list[str] = []
    delegatorWeights: list[int] = []
    delegatorProofs: list[list[str]] = []


class DelegateBody(BaseModel):
    daoId: int
    to: str


def _xlayer() -> XLayerClient:
    return XLayerClient(
        rpc_url=os.environ["XLAYER_RPC"],
        private_key=os.environ["RELAYER_PK"],
        registry=os.environ["REGISTRY_ADDR"],
        proposal_registry=os.environ["PROPOSAL_ADDR"],
        delegation=os.environ["DELEGATION_ADDR"],
        voting=os.environ["VOTING_ADDR"],
    )


def _genlayer() -> GovAIClient:
    return GovAIClient(
        contract_address=os.environ["GENLAYER_CONTRACT"],
        account=os.environ["GENLAYER_ACCOUNT"],
        network=os.environ.get("GENLAYER_NETWORK", "testnet"),
    )


def _supported_chains() -> dict:
    raw = os.getenv("GOVAI_SUPPORTED_CHAINS", "[]")
    return {int(c["chainId"]): c for c in json.loads(raw)}


# ---- endpoints ----
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/daos")
def register_dao(payload: RegisterDAO):
    cid = ipfs.add_json({"name": payload.name, "mission": payload.mission, "text": payload.constitution})
    x = _xlayer()
    cfg = payload.model_dump()
    cfg["constitutionCid"] = cid
    dao_id = x.register_dao(cfg)
    DAOS[dao_id] = {**payload.model_dump(), "constitutionCid": cid}
    return {"daoId": dao_id, "constitutionCid": cid}


@app.get("/daos")
def list_daos():
    return [{"daoId": i, **c} for i, c in DAOS.items()]


@app.post("/proposals")
def submit_proposal(payload: SubmitProposal):
    if payload.daoId not in DAOS:
        raise HTTPException(404, "unknown DAO")
    cid = ipfs.add_json({"title": payload.title, "body": payload.body})
    constitution_cid = DAOS[payload.daoId]["constitutionCid"]
    x = _xlayer()
    pid = x.submit_proposal(payload.daoId, cid, constitution_cid)
    PROPOSALS[pid] = {"daoId": payload.daoId, "title": payload.title, "body": payload.body}
    PROPOSAL_CIDS[pid] = (cid, constitution_cid)
    return {"proposalId": pid}


def _do_ai_review_sync(task_id: str, pid: int, proposal_cid: str, constitution_cid: str) -> None:
    """Blocking AI-review work, executed in a thread so the endpoint can return immediately.
    Writes the result (or error) into TASKS so the client can poll GET /tasks/{task_id}."""
    try:
        x = _xlayer()
        g = _genlayer()
        flat = run_ai_review(
            x, g, pid, proposal_cid, constitution_cid,
            supported_chains=_supported_chains(),
            xlayer_chain_id=int(os.getenv("XLAYER_CHAIN_ID", "0")),
            member_count=len(PROPOSALS),
        )
        TASKS[task_id] = {"taskId": task_id, "proposalId": pid, "status": "done", "result": flat}
    except Exception as e:
        TASKS[task_id] = {"taskId": task_id, "proposalId": pid, "status": "error", "error": str(e)}


@app.post("/proposals/{pid}/run-ai")
async def run_ai(pid: int):
    """Kick off the AI review asynchronously. Returns a taskId; poll GET /tasks/{task_id}.

    GenLayer's `wait_for_transaction_receipt(..., status=FINALIZED)` can take minutes for
    comparative consensus. Running the blocking work in a background thread lets this
    request return immediately and gives the review room to finish on Vercel serverless.
    State lives in the in-memory TASKS dict (resets on cold start; swap in Vercel KV /
    Postgres for production).
    """
    if pid not in PROPOSAL_CIDS:
        raise HTTPException(404, "unknown proposal")
    proposal_cid, constitution_cid = PROPOSAL_CIDS[pid]
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"taskId": task_id, "proposalId": pid, "status": "processing"}
    asyncio.create_task(
        asyncio.to_thread(_do_ai_review_sync, task_id, pid, proposal_cid, constitution_cid)
    )
    return {"taskId": task_id, "proposalId": pid, "status": "processing"}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Poll the status of an async AI-review task."""
    if task_id not in TASKS:
        raise HTTPException(404, "unknown task")
    return TASKS[task_id]


@app.get("/proposals/{pid}")
def get_proposal(pid: int):
    x = _xlayer()
    prop = x.get_proposal(pid)
    meta = PROPOSALS.get(pid, {})
    return {**prop, "title": meta.get("title"), "body": meta.get("body")}


@app.get("/proposals")
def list_proposals():
    x = _xlayer()
    out = []
    items = []
    for pid, meta in PROPOSALS.items():
        prop = x.get_proposal(pid)
        out.append({
            "id": pid,
            "daoId": prop["daoId"],
            "daoName": DAOS.get(prop["daoId"], {}).get("name", ""),
            "title": meta.get("title", ""),
            "riskScore": prop["aiReport"]["riskScore"] if prop["aiReport"] else None,
            "selfDealing": prop["aiReport"]["selfDealing"] if prop["aiReport"] else None,
            "malicious": prop["aiReport"]["malicious"] if prop["aiReport"] else None,
            "stage": prop["stage"],
        })
        items.append({"id": pid, "title": meta.get("title", ""), "body": meta.get("body", "")})
    summaries = summarize_batch(items)
    for o in out:
        o["summary"] = summaries.get(o["id"], "")
    return out


@app.post("/proposals/{pid}/vote")
def vote(pid: int, body: VoteBody):
    x = _xlayer()
    x.cast_vote(
        proposal_id=pid,
        dao_id=body.daoId,
        token=body.token,
        chain_id=body.chainId,
        support=body.support,
        claimed_weight=body.claimedWeight,
        proof=body.proof,
        delegators=body.delegators,
        delegator_weights=body.delegatorWeights,
        delegator_proofs=body.delegatorProofs,
    )
    return {"ok": True}


@app.post("/proposals/{pid}/finalize")
def finalize(pid: int):
    _xlayer().finalize(pid)
    return {"ok": True}


@app.post("/daos/{dao_id}/delegate")
def delegate(dao_id: int, body: DelegateBody):
    _xlayer().delegate(dao_id, body.to)
    return {"ok": True}
