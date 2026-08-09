# GovAI prompt catalog (GenLayer AI brain)

The GenLayer Intelligent Contract `govai_decision.py` runs two LLM judgements per proposal,
both under **comparative consensus** (GenLayer's Equivalence Principle: a leader executes,
validators independently re-run and compare). The canonical prompt text lives in
`contracts/genlayer/prompts/*.txt` and is embedded in the contract.

## 1. Alignment — `PROMPT_ALIGN` (`align.txt`)
Decides whether the proposal **advances or contradicts** the DAO's mission & constitution.

Output (JSON):
```json
{
  "aligned": boolean,
  "confidence": 0.0-1.0,
  "conflicts": ["clause A", "clause B"],
  "reasoning": "string"
}
```
Consensus: `EqComparative` template — `aligned` and `confidence` must agree (within 0.2);
`reasoning` may differ. Falls back to a deterministic tolerance validator if the internal
`gl_call` module is unavailable.

## 2. Scoring & abuse flags — `PROMPT_SCORE` (`score.txt`)
Scores intent clarity, benefit, and risk; flags self-dealing and malicious content.

Output (JSON):
```json
{
  "intent_clarity": 0-100,
  "benefit_score": 0-100,
  "risk_score": 0-100,
  "self_dealing_flag": boolean,
  "malicious_flag": boolean,
  "red_flags": ["..."],
  "rationale": "string"
}
```
Consensus: deterministic **numeric tolerance validator** (±10 on each score; boolean flags
must match exactly). This is stricter and more reproducible than LLM comparison for numbers.

## 3. Threshold gate (deterministic, no LLM)
After both judgements, the contract applies the DAO's configured thresholds:

```
passed =
    aligned
    AND (not block_self_dealing OR not self_dealing_flag)
    AND (not block_malicious OR not malicious_flag)
    AND risk_score <= max_risk
    AND benefit_score >= min_benefit
    AND confidence >= min_confidence
```

If `passed` → X Layer opens voting. Else → proposal is `Rejected` with a human-readable
reason listing every failed condition (auditable).

## Tuning
- Pin the model and keep JSON validators structural (never `strict_eq`) — LLM outputs are
  non-deterministic by design.
- For demos, widen thresholds (higher `max_risk`, lower `min_benefit`) so good proposals pass.
- The `appeal()` entrypoint re-runs the full comparative-consensus review for disputes.
