"""Minimal IPFS client.

Stores proposal text, DAO constitutions, and AI reports on IPFS and reads them back.
Uses Pinata when PINATA_API_KEY / PINATA_API_SECRET are set; otherwise falls back to a
configurable public gateway for reads and a local node `/api/v0/add` for writes.

The GovAI GenLayer contract reads CIDs via `gl.nondet.web.get(<gateway>/<cid>)`.
"""
import os
import json
import httpx


class IPFSClient:
    def __init__(
        self,
        gateway: str = "https://ipfs.io/ipfs/",
        pinata_key: str | None = None,
        pinata_secret: str | None = None,
        node_url: str = "http://127.0.0.1:5001",
    ):
        self.gateway = gateway.rstrip("/") + "/"
        self.pinata_key = pinata_key or os.getenv("PINATA_API_KEY")
        self.pinata_secret = pinata_secret or os.getenv("PINATA_API_SECRET")
        self.node_url = node_url

    def add_json(self, data: dict) -> str:
        """Pin JSON and return the IPFS CID."""
        if self.pinata_key and self.pinata_secret:
            resp = httpx.post(
                "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                json={"pinataContent": data},
                headers={"pinata_api_key": self.pinata_key, "pinata_secret_api_key": self.pinata_secret},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["IpfsHash"]
        # Fallback: local node add.
        resp = httpx.post(f"{self.node_url}/api/v0/add", files={"file": ("data.json", json.dumps(data))}, timeout=30)
        resp.raise_for_status()
        return resp.text.split('"Hash":"')[1].split('"')[0]

    def get_json(self, cid: str) -> dict:
        resp = httpx.get(self.gateway + cid, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, cid: str) -> str:
        resp = httpx.get(self.gateway + cid, timeout=30)
        resp.raise_for_status()
        return resp.text
