# Supported chains for cross-chain token verification

GovAI verifies a DAO's token holdings at a snapshot block to compute voting weight. A DAO
may set **any EVM chain** as its token chain, but GovAI can only *verify* holdings for
chains whose block explorer exposes an **Etherscan-compatible API** (used to enumerate
token holders via `module=account&action=tokentx`) plus an RPC endpoint (used for
`balanceOf` at a specific block).

## Verified-compatible explorers (Etherscan family)

| Chain | chainId | Explorer API base | Notes |
|-------|---------|-------------------|-------|
| Ethereum | 1 | https://api.etherscan.io/api | mainnet |
| Base | 8453 | https://api.basescan.org/api | |
| Arbitrum One | 42161 | https://api.arbiscan.io/api | |
| Optimism | 10 | https://api.optimistic.etherscan.io/api | |
| Polygon PoS | 137 | https://api.polygonscan.com/api | |
| X Layer (OKX) | 195 | https://api.xlayerscan.io/api *(confirm)* | if Etherscan-powered; otherwise used as the *voting* chain (native mode) |
| Sepolia / Holesky | 11155111 / 17000 | respective testnet explorers | for demos |

## How it works
1. `ChainExplorer.get_holders(token, block)` scans `tokentx` to collect holder addresses.
2. For each holder, `balance_of(token, addr, block)` snapshots the weight at the block.
3. `build_snapshot` builds a Merkle tree `(voter -> weight)` and returns the root + total.
4. The relayer stores the root on X Layer (`TokenWeight.setSnapshotRoot`); voters prove
   their weight with a Merkle proof when casting a vote.

## Caveats
- Historical `balanceOf` at an arbitrary block depends on the RPC/explorer retaining
  archive state. If a chain only exposes latest state, the relayer falls back to a recent
  block (documented in the runbook).
- Unverified chains: the DAO can still register, but must place its token on X Layer
  (native mode) or supply its own holder snapshot out-of-band.
