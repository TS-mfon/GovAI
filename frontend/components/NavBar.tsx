"use client";

import Link from "next/link";
import { useAccount, useConnect, useDisconnect } from "wagmi";

export function NavBar() {
  const { address, isConnected } = useAccount();
  const { connect, connectors } = useConnect();
  const { disconnect } = useDisconnect();

  return (
    <nav className="topbar">
      <span className="brand">GovAI</span>
      <Link href="/">Dashboard</Link>
      <Link href="/daos/onboard">Onboard DAO</Link>
      <Link href="/proposals/submit">Submit Proposal</Link>
      <span className="spacer" />
      {isConnected ? (
        <button className="secondary" onClick={() => disconnect()}>
          {address?.slice(0, 6)}…{address?.slice(-4)}
        </button>
      ) : (
        <button onClick={() => connect({ connector: connectors[0] })}>Connect Wallet</button>
      )}
    </nav>
  );
}
