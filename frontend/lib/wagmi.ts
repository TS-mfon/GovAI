"use client";

import { http, createConfig } from "wagmi";
import { injected } from "wagmi/connectors";
import { defineChain } from "viem";

const rpc = process.env.NEXT_PUBLIC_XLAYER_RPC || "https://testrpc.xlayer.tech";
const chainId = Number(process.env.NEXT_PUBLIC_XLAYER_CHAIN_ID || 195);
const explorer = process.env.NEXT_PUBLIC_XLAYER_EXPLORER || "https://scan.xlayer.tech";

// X Layer (OKX L2) — confirm the testnet chainId / RPC with the current X Layer docs.
export const xlayer = defineChain({
  id: chainId,
  name: "X Layer",
  network: "xlayer",
  nativeCurrency: { name: "OKB", symbol: "OKB", decimals: 18 },
  rpcUrls: { default: { http: [rpc] } },
  blockExplorers: { default: { name: "X Layer Scan", url: explorer } },
  testnet: true,
});

export const wagmiConfig = createConfig({
  chains: [xlayer],
  connectors: [injected()],
  transports: { [chainId]: http() },
  ssr: true,
});
