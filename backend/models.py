"""Shared data models for the GovAI backend / API."""
from typing import Optional
from pydantic import BaseModel


class DAOConfig(BaseModel):
    name: str
    mission: str
    constitutionCid: str  # IPFS CID of the constitution text
    token: str = "0x0000000000000000000000000000000000000000"  # zero => no token
    chainId: int = 0  # chain the token lives on (0 if no token)
    maxRisk: int = 60  # 0-100
    minBenefit: int = 40  # 0-100
    minConfidence: int = 60  # 0-100
    votingDuration: int = 3 * 24 * 3600  # seconds
    quorumBps: int = 4000  # 0-10000 (40%)
    delegationOn: bool = True


class AIReport(BaseModel):
    passed: bool
    reason: str
    intentClarity: int
    benefitScore: int
    riskScore: int
    selfDealing: bool
    malicious: bool
    confidence: int  # 0-100


class Proposal(BaseModel):
    id: int
    daoId: int
    proposer: str
    proposalCid: str
    constitutionCid: str
    stage: str
    aiReport: Optional[AIReport] = None
    votingEndsAt: int = 0


class ProposalSummary(BaseModel):
    id: int
    daoId: int
    daoName: str
    title: str
    summary: str  # AI-generated plain-language summary (cross-DAO feed)
    riskScore: Optional[int] = None
    selfDealing: Optional[bool] = None
    malicious: Optional[bool] = None
    stage: str
