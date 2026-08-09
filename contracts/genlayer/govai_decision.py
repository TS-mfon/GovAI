"""
GovAI — AI DAO Governance Copilot
GenLayer Intelligent Contract: the AI / decision brain.

Responsibilities
----------------
1. ALIGNMENT   : Does a proposal advance or contradict the DAO's mission & constitution?
2. SCORING     : Risk / intent-clarity / benefit scores + self-dealing & malicious flags.
3. THRESHOLD   : Deterministic gate against the DAO's configured thresholds.
All non-deterministic (LLM) steps use GenLayer's comparative consensus (Equivalence
Principle): a leader executes, validators independently re-run and compare. Subjective
fields are compared with the `EqComparative` prompt template; numeric scores use a
deterministic tolerance validator. This is the "GenLayer prompt comparative consensus".

Deploys to GenLayer testnet via the GenLayer CLI / genlayer-py client
(see ../../deploy/deploy_genlayer.py).

NOTE: imports/paths follow the GenLayer SDK as documented at docs.genlayer.com.
Verify the exact module layout (`genlayer` vs `genvm`) against the SDK version
you install; the *logic* below is chain-agnostic.
"""

from genlayer import gl

try:
    import genlayer.gl._internal.gl_call as gl_call
    from genlayer.gl.nondet import _decode_nondet
except Exception:  # pragma: no cover - depends on SDK internals
    gl_call = None
    _decode_nondet = None


# ---------------------------------------------------------------------------
# Prompt templates (canonical catalog also lives in ./prompts/*.txt)
# ---------------------------------------------------------------------------
PROMPT_ALIGN = """\
You are the governance alignment reviewer for a decentralised autonomous organisation.
Below is the DAO's mission and constitution, followed by a proposed action.

=== DAO MISSION & CONSTITUTION ===
{constitution}

=== PROPOSAL ===
{proposal}

Decide whether the proposal ADVANCES or CONTRADICTS the DAO's stated mission and
constitution. Be strict: if the proposal conflicts with any explicit rule or clearly
diverts from the mission, set aligned=false.

Return ONLY a JSON object with exactly these keys:
{{
  "aligned": boolean,
  "confidence": float between 0.0 and 1.0,
  "conflicts": array of short strings citing the specific constitution clauses or mission points that conflict (empty if none),
  "reasoning": string, 2-4 sentences
}}
"""

PROMPT_SCORE = """\
You are a risk & value analyst for a decentralised autonomous organisation.
Assess the proposal below against the DAO's mission and constitution.

=== DAO MISSION & CONSTITUTION ===
{constitution}

=== PROPOSAL ===
{proposal}

Score the proposal and flag abuse. Be conservative and specific.

Return ONLY a JSON object with exactly these keys:
{{
  "intent_clarity": integer 0-100 (how clearly the proposal states its goal and mechanism),
  "benefit_score": integer 0-100 (expected benefit to the DAO if passed),
  "risk_score": integer 0-100 (execution / financial / reputational risk),
  "self_dealing_flag": boolean (true if the proposer or their associates directly benefit financially or politically from the proposal),
  "malicious_flag": boolean (true if the proposal is harmful, deceptive, or an attack on the DAO),
  "red_flags": array of short strings describing concrete concerns (empty if none),
  "rationale": string, 3-5 sentences justifying the scores and flags
}}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fetch_text(cid: str) -> str:
    """Fetch text content stored on IPFS via GenLayer's web-data-access feature."""
    gateway = "https://ipfs.io/ipfs/"
    resp = gl.nondet.web.get(gateway + cid)
    body = getattr(resp, "body", None) or getattr(resp, "text", "") or ""
    if isinstance(body, (bytes, bytearray)):
        body = bytes(body).decode("utf-8", "replace")
    return body


def _run_llm_json(prompt: str):
    """Call the LLM and parse JSON (GenLayer non-determinism feature)."""
    return gl.nondet.exec_prompt(prompt, response_format="json")


def _valid_align(d: object) -> bool:
    if not isinstance(d, dict):
        return False
    if not isinstance(d.get("aligned"), bool):
        return False
    c = d.get("confidence")
    if not (isinstance(c, (int, float)) and 0.0 <= float(c) <= 1.0):
        return False
    if not isinstance(d.get("conflicts"), list):
        return False
    if not isinstance(d.get("reasoning"), str):
        return False
    return True


def _valid_scores(d: object) -> bool:
    if not isinstance(d, dict):
        return False
    for k in ("intent_clarity", "benefit_score", "risk_score"):
        v = d.get(k)
        if not (isinstance(v, int) and 0 <= int(v) <= 100):
            return False
    if not isinstance(d.get("self_dealing_flag"), bool):
        return False
    if not isinstance(d.get("malicious_flag"), bool):
        return False
    if not isinstance(d.get("red_flags"), list):
        return False
    if not isinstance(d.get("rationale"), str):
        return False
    return True


def _validate_alignment_comparative(leader_result, leader_fn) -> bool:
    """Comparative consensus for the subjective alignment decision.

    Validators re-run the prompt and compare via the EqComparative prompt template,
    which asks: do `aligned` and `confidence` agree (reasoning may differ)?
    """
    if not isinstance(leader_result, gl.vm.Return):
        return False
    if not _valid_align(leader_result.calldata):
        return False
    if gl_call is None or _decode_nondet is None:
        # Fallback: deterministic tolerance comparison.
        return _validate_alignment_tolerant(leader_result, leader_fn)
    validator_data = leader_fn()
    verdict = gl_call.gl_call_generic(
        {
            "ExecPromptTemplate": {
                "template": "EqComparative",
                "leader_answer": format(leader_result.calldata),
                "validator_answer": format(validator_data),
                "principle": "`aligned` boolean and `confidence` (within 0.2) must match; `reasoning` may differ.",
            }
        },
        _decode_nondet,
    ).get()
    return bool(verdict)


def _validate_alignment_tolerant(leader_result, leader_fn) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    leader = leader_result.calldata
    if not _valid_align(leader):
        return False
    mine = leader_fn()
    if not _valid_align(mine):
        return False
    if bool(leader["aligned"]) != bool(mine["aligned"]):
        return False
    if abs(float(leader["confidence"]) - float(mine["confidence"])) > 0.2:
        return False
    return True


def _validate_scores_tolerant(leader_result, leader_fn) -> bool:
    """Comparative consensus for numeric scores: re-run and require values within
    tolerance and identical boolean flags (deterministic, no LLM comparison needed)."""
    if not isinstance(leader_result, gl.vm.Return):
        return False
    leader = leader_result.calldata
    if not _valid_scores(leader):
        return False
    mine = leader_fn()
    if not _valid_scores(mine):
        return False
    tol = 10
    for k in ("intent_clarity", "benefit_score", "risk_score"):
        if abs(int(leader[k]) - int(mine[k])) > tol:
            return False
    if bool(leader["self_dealing_flag"]) != bool(mine["self_dealing_flag"]):
        return False
    if bool(leader["malicious_flag"]) != bool(mine["malicious_flag"]):
        return False
    return True


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
class GovAIDecision:
    def __init__(self):
        # dao_id -> threshold config
        self.dao_config: dict = {}
        # proposal_id -> review result (auditable)
        self.reviews: dict = {}
        # proposal_id -> "PASSED" | "REJECTED"
        self.status: dict = {}

    # ---- DAO configuration (called by the relayer when a DAO registers) ----
    @gl.public.write
    def register_dao(
        self,
        dao_id: str,
        max_risk: int,
        min_benefit: int,
        min_confidence: float,
        block_self_dealing: bool = True,
        block_malicious: bool = True,
    ):
        self.dao_config[dao_id] = {
            "max_risk": int(max_risk),
            "min_benefit": int(min_benefit),
            "min_confidence": float(min_confidence),
            "block_self_dealing": bool(block_self_dealing),
            "block_malicious": bool(block_malicious),
        }

    # ---- Core: review a proposal ----
    @gl.public.write
    def review_proposal(
        self,
        dao_id: str,
        proposal_id: str,
        constitution_cid: str,
        proposal_cid: str,
    ) -> dict:
        cfg = self.dao_config.get(dao_id)
        if cfg is None:
            raise Exception(f"DAO {dao_id} not registered")

        constitution = _fetch_text(constitution_cid)
        proposal = _fetch_text(proposal_cid)

        # 1) ALIGNMENT — comparative consensus (EqComparative)
        align_prompt = PROMPT_ALIGN.format(constitution=constitution, proposal=proposal)
        alignment = gl.vm.run_nondet_unsafe(
            lambda: _run_llm_json(align_prompt),
            lambda lr: _validate_alignment_comparative(lr, lambda: _run_llm_json(align_prompt)),
        )

        # 2) SCORING — comparative consensus (numeric tolerance validator)
        score_prompt = PROMPT_SCORE.format(constitution=constitution, proposal=proposal)
        scores = gl.vm.run_nondet_unsafe(
            lambda: _run_llm_json(score_prompt),
            lambda lr: _validate_scores_tolerant(lr, lambda: _run_llm_json(score_prompt)),
        )

        # 3) THRESHOLD GATE — deterministic, no LLM
        passed = (
            bool(alignment["aligned"])
            and (not cfg["block_self_dealing"] or not bool(scores["self_dealing_flag"]))
            and (not cfg["block_malicious"] or not bool(scores["malicious_flag"]))
            and int(scores["risk_score"]) <= int(cfg["max_risk"])
            and int(scores["benefit_score"]) >= int(cfg["min_benefit"])
            and float(alignment["confidence"]) >= float(cfg["min_confidence"])
        )

        if not passed:
            reasons = []
            if not alignment["aligned"]:
                reasons.append("fails alignment with mission/constitution")
            if cfg["block_self_dealing"] and scores["self_dealing_flag"]:
                reasons.append("self-dealing detected")
            if cfg["block_malicious"] and scores["malicious_flag"]:
                reasons.append("malicious content detected")
            if int(scores["risk_score"]) > int(cfg["max_risk"]):
                reasons.append(f"risk {scores['risk_score']} > max {cfg['max_risk']}")
            if int(scores["benefit_score"]) < int(cfg["min_benefit"]):
                reasons.append(f"benefit {scores['benefit_score']} < min {cfg['min_benefit']}")
            if float(alignment["confidence"]) < float(cfg["min_confidence"]):
                reasons.append("alignment confidence below threshold")
            report = {
                "dao_id": dao_id,
                "proposal_id": proposal_id,
                "passed": False,
                "reason": "; ".join(reasons),
                "alignment": alignment,
                "scores": scores,
            }
        else:
            report = {
                "dao_id": dao_id,
                "proposal_id": proposal_id,
                "passed": True,
                "reason": "passed AI gate",
                "alignment": alignment,
                "scores": scores,
            }

        self.reviews[proposal_id] = report
        self.status[proposal_id] = "PASSED" if passed else "REJECTED"
        return report

    # ---- Appeal: second comparative-consensus review (GenLayer appeal process) ----
    @gl.public.write
    def appeal(
        self,
        dao_id: str,
        proposal_id: str,
        constitution_cid: str,
        proposal_cid: str,
    ) -> dict:
        # Re-runs the full review; a fresh leader+validators set produces an
        # independent comparative-consensus verdict (the dispute / appeal flow).
        return self.review_proposal(dao_id, proposal_id, constitution_cid, proposal_cid)

    # ---- Read stored review (auditability / transparency) ----
    @gl.public.view
    def get_review(self, proposal_id: str) -> dict:
        if proposal_id not in self.reviews:
            raise Exception("unknown proposal")
        return self.reviews[proposal_id]
