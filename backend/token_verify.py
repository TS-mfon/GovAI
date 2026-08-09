"""Cross-chain token verification + Merkle voting-weight snapshots.

Problem: a DAO's token may live on a chain other than X Layer (where voting happens).
We verify holdings at a snapshot block using the chain's Etherscan-compatible explorer
API / RPC, then build a Merkle tree (voter -> weight) so voters can prove their weight
on X Layer without the voting chain trusting the external chain.

Only chains whose explorer API we support are selectable by the DAO at registration.
"""
import httpx
from typing import Iterable
from eth_hash.auto import keccak
from web3 import Web3


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _leaf(addr: str, weight: int) -> bytes:
    return keccak(bytes.fromhex(addr[2:]) + weight.to_bytes(32, "big"))


def _hash_pair(a: bytes, b: bytes) -> bytes:
    # Order-independent pairing — MUST match OpenZeppelin's MerkleProof.verify, which
    # sorts each pair by hash value before hashing. Building the tree with a fixed
    # left+right order would make the root never match on-chain verification.
    return keccak(a + b) if a <= b else keccak(b + a)


class MerkleTree:
    """Binary Merkle tree over (address, weight) leaves. Deterministic (sorted)."""

    def __init__(self, entries: Iterable[tuple[str, int]]):
        self.entries = sorted(((a, int(w)) for a, w in entries), key=lambda e: e[0].lower())
        leaves = [_leaf(a, w) for a, w in self.entries]
        if not leaves:
            leaves = [keccak(b"")]
        self.tree = [leaves]
        while len(self.tree[-1]) > 1:
            lvl = self.tree[-1]
            nxt = []
            for i in range(0, len(lvl), 2):
                left = lvl[i]
                right = lvl[i + 1] if i + 1 < len(lvl) else left
                nxt.append(_hash_pair(left, right))
            self.tree.append(nxt)
        self.root: bytes = self.tree[-1][0]

    def proof(self, addr: str, weight: int) -> list[bytes]:
        idx = next(i for i, (a, w) in enumerate(self.entries) if a.lower() == addr.lower() and w == weight)
        proof: list[bytes] = []
        i = idx
        for level in self.tree[:-1]:
            sibling = i ^ 1
            proof.append(level[sibling] if sibling < len(level) else level[i])
            i //= 2
        return proof

    def proof_hex(self, addr: str, weight: int) -> list[str]:
        return ["0x" + p.hex() for p in self.proof(addr, weight)]


class ChainExplorer:
    """Reads ERC-20 balances/total supply and enumerates holders via an
    Etherscan-compatible explorer API + RPC."""

    def __init__(self, rpc_url: str, api_url: str | None = None, api_key: str | None = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.api_url = api_url
        self.api_key = api_key

    def balance_of(self, token: str, owner: str, block: int) -> int:
        c = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
        return c.functions.balanceOf(Web3.to_checksum_address(owner)).call(block_identifier=block)

    def total_supply(self, token: str, block: int) -> int:
        c = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
        return c.functions.totalSupply().call(block_identifier=block)

    def get_holders(self, token: str, block: int) -> dict[str, int]:
        """Enumerate token holders by scanning Transfer events via the explorer API,
        then snapshot each holder's balance at `block`."""
        if not self.api_url:
            raise RuntimeError("api_url required to enumerate holders")
        token = Web3.to_checksum_address(token)
        addresses: set[str] = set()
        page = 1
        while True:
            r = httpx.get(
                self.api_url,
                params={
                    "module": "account",
                    "action": "tokentx",
                    "contractaddress": token,
                    "page": page,
                    "offset": 1000,
                    "sort": "asc",
                    "apikey": self.api_key or "",
                },
                timeout=30,
            ).json()
            txs = r.get("result") or []
            if not isinstance(txs, list) or not txs:
                break
            for t in txs:
                addresses.add(t["from"].lower())
                addresses.add(t["to"].lower())
            if len(txs) < 1000:
                break
            page += 1
        return {a: self.balance_of(token, a, block) for a in addresses}


def build_snapshot(token: str, explorer: ChainExplorer, block: int):
    """Return (merkle_root_hex, total_weight, entries) for an external-chain token."""
    holders = explorer.get_holders(token, block)
    entries = [(a, w) for a, w in holders.items() if w > 0]
    total_weight = sum(w for _, w in entries)
    tree = MerkleTree(entries)
    return "0x" + tree.root.hex(), total_weight, entries
