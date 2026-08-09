# GovAI — AI DAO Governance Copilot

> Summarizes proposals across cross-Layer DAOs, flags self-dealing/malicious proposals,
> scores risk / intent / benefits, and runs **real** token-weighted, delegated voting.
> **GenLayer** = AI brain. **X Layer (OKX L2)** = on-chain governance.
> **Etherscan-compatible API** = cross-chain token verification.

No vote simulation — only transparency and real turnout tracking.

---

## Architecture

```
                ┌─────────────────────────┐
   DAO / person │  Frontend (Next.js)     │  onboard, submit, view AI report, vote
                └───────────┬─────────────┘
                            │  REST
                ┌───────────▼─────────────┐
                │  Backend (FastAPI)       │  indexer · IPFS · summarizer · RELAYER
                └─────┬──────────────┬─────┘
        review_proposal│              │ submitAIReport / setVotingSnapshot / castVote
                      ▼              ▼
        ┌──────────────────┐   ┌──────────────────────────┐
        │ GenLayer testnet  │   │ X Layer (OKX L2) testnet  │
        │ AI brain          │   │ GovAIRegistry             │
        │  - alignment      │   │ ProposalRegistry          │
        │  - scoring        │   │ Voting + Delegation       │
        │  - threshold gate │   │ TokenWeight (native/Merkle)│
        └──────────────────┘   └──────────────────────────┘
                                      ▲ token weight
                                      │ (native balanceOf OR Etherscan→Merkle)
                                external EVM chains
```

**Flow**
1. DAO registers on X Layer (`GovAIRegistry`) with mission, constitution, optional token, thresholds.
2. Member submits a proposal → IPFS → `ProposalRegistry.submitProposal` (stage `Submitted`).
3. Backend relayer calls GenLayer `review_proposal` (comparative consensus: alignment + scoring + threshold gate).
4. GenLayer returns verdict + scores → relayer calls `submitAIReport` (stage `Voting` or `Rejected`).
5. For external-chain tokens, relayer verifies holdings via Etherscan, builds a Merkle snapshot, and calls `setVotingSnapshot`.
6. Token holders vote (weighted, with delegation) on X Layer; `finalize()` applies quorum + majority.

---

## Repo layout

```
govai/
  contracts/genlayer/   govai_decision.py + prompts/      (GenLayer AI brain)
  contracts/xlayer/     GovAIRegistry, ProposalRegistry,  (X Layer on-chain governance)
                        Voting, Delegation, TokenWeight, interfaces/
  backend/              FastAPI: token_verify (Etherscan+Merkle), chain, genlayer_client,
                        relayer, summarizer, ipfs, main.py
  frontend/             Next.js: dashboard, DAO onboarding, submit, proposal detail + vote
  deploy/               hardhat.config.js, 00_deploy_xlayer.js, deploy_genlayer.py
  docs/                 SUPPORTED_CHAINS.md, PROMPT_CATALOG.md
```

---

## Quickstart

### 1. GenLayer (AI brain)
```bash
pip install genlayer-py
GENLAYER_ACCOUNT=0x... GENLAYER_NETWORK=testnet python deploy/deploy_genlayer.py
# note the deployed contract address -> GENLAYER_CONTRACT
```

### 2. X Layer (governance)
```bash
cd deploy && npm install
XLAYER_RPC=https://testrpc.xlayer.tech DEPLOYER_PK=0x... XLAYER_CHAIN_ID=195 \
  RELAYER_ADDR=0x... npx hardhat run 00_deploy_xlayer.js --network xlayerTestnet
# writes deployed.json -> fill REGISTRY_ADDR / PROPOSAL_ADDR / DELEGATION_ADDR / VOTING_ADDR
```

### 3. Backend
```bash
cd backend && pip install -r requirements.txt
cp .env.example .env   # fill addresses, keys, supported chains
uvicorn main:app --reload --port 8000
```

### 4. Frontend
```bash
cd frontend && npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL + contract addresses
npm run dev   # http://localhost:3000
```

### 5. End-to-end demo
1. Onboard a DAO (frontend `/daos/onboard` or `POST /daos`).
2. Submit a proposal (`/proposals/submit` or `POST /proposals`).
3. Run the AI review: `POST /proposals/<id>/run-ai` (relayer → GenLayer → X Layer).
4. Open the proposal page, connect wallet, cast a weighted vote.
5. When the window closes: `POST /proposals/<id>/finalize`.

---

## Local development (Anvil)

The backend `.env` ships pointing at a local Hardhat/Anvil node so the full stack is
runnable end-to-end without testnet credentials. Use this path for the vertical-slice demo.

### 0. Start a local chain
```bash
# either:
npx hardhat node                 # in deploy/  (chainId 31337, 20 prefunded accounts)
# or:
anvil                            # foundry (chainId 31337, 10 prefunded accounts)
```
The shipped `deploy/hardhat.config.js` `localhost` network already targets `http://127.0.0.1:8545`.
The default Anvil/Hardhat account #0 private key
(`0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`)
is pre-set as `RELAYER_PK` in `backend/.env`.

### 1. Deploy the X Layer governance contracts locally
```bash
cd deploy
npx hardhat compile               # compiles GovAI + OpenZeppelin v5
npx hardhat run 00_deploy_xlayer.js --network localhost   # writes deployed.json
```
Copy the four addresses from `deployed.json` into `backend/.env`
(`REGISTRY_ADDR`, `PROPOSAL_ADDR`, `DELEGATION_ADDR`, `VOTING_ADDR`)
and into `frontend/.env.local` (`NEXT_PUBLIC_*`).

### 2. Deploy the GenLayer intelligent contract
The GenLayer testnet can't be mocked locally, so for a full local demo deploy to
`testnet_asimov` (or `studionet`) and set `GENLAYER_CONTRACT` + `GENLAYER_ACCOUNT`
in `backend/.env`. For the contracts-only slice, you can skip the GenLayer call and
call `POST /proposals/<id>/vote` directly after stubbing an AI report.

### 3. Boot the stack (three terminals)
```bash
# T1 - backend
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# T2 - frontend
cd frontend
npm run dev    # http://localhost:3000

# T3 - your local chain (already running from step 0)
```

Verify it works:
```bash
curl http://127.0.0.1:8000/health          # {"status":"ok"}
curl http://127.0.0.1:8000/docs            # Swagger UI
curl http://127.0.0.1:8000/daos            # []
curl http://127.0.0.1:8000/proposals       # []
```

---

## Key design points
- **Permissionless & multi-tenant**: any DAO can register; token optional.
- **Two token-weight modes**: native X Layer ERC20 (`balanceOf`) or external EVM token
  (Etherscan-verified → Merkle-proof on X Layer).
- **Comparative consensus**: subjective alignment via `EqComparative`; numeric scores via a
  deterministic tolerance validator. See `docs/PROMPT_CATALOG.md`.
- **Auditable**: every AI decision stores alignment, scores, flags, and the rejection reason.
- **No vote simulation**: we show real quorum/turnout progress only.

## Open questions / verify at build time
- Exact `genlayer_py` / `genlayer` SDK import paths (logic is chain-agnostic).
- X Layer testnet RPC / chainId / faucet (currently assumed `195`; confirm with X Layer docs).
- `GenLayer → EVM` direct `.emit()` to X Layer (we use a backend relayer as the robust path).
- Historical `balanceOf` archive support per chain (see `docs/SUPPORTED_CHAINS.md`).

---

## Build notes (gotchas hit while wiring this up)

These are the non-obvious fixes already applied to the repo so you don't re-debug them:

| Symptom | Root cause | Fix |
|---|---|---|
| `Hardhat HH1007: ... is treated as local but is outside the project` | `paths.sources` pointed outside the Hardhat project root | `deploy/contracts/` is a junction → `../contracts`; `paths.sources: "./contracts/xlayer"` |
| `CompilerError: ... needs ^0.8.20` (OZ v5 MerkleProof, Ownable, ...) | Hardhat pinned to `0.8.19` only | `compilers: [{0.8.20, viaIR + optimizer}, {0.8.19, same}]` |
| `Stack too deep` in `Voting.sol:63` | 6-arg `weightOf` call overflows 16 EVM stack slots | enable `viaIR: true` + optimizer |
| `cannot import name 'Client' from 'genlayer_py'` | SDK 0.18.x exposes `create_client(...)`, not `Client` | `backend/genlayer_client.py` rewritten against `create_client(chain, endpoint, account)` + `read_contract` / `write_contract` |
| `ERESOLVE ... @tanstack/react-query@5.51.0` (404) | exact pin `5.51.0` was never published | `package.json` uses `^5.51.0` (resolves to 5.101.4); install with `--legacy-peer-deps` for wagmi's MetaMask transitive peers |
| `lodash _isFlattenable: Cannot find module './isArguments'` | partial `node_modules` from an interrupted install | `rm -rf node_modules package-lock.json && npm install`, then verify completeness |
