"use client";

import { useWriteContract } from "wagmi";
import { useState } from "react";
import { votingAbi, VOTING_ADDR } from "@/lib/contracts";

const ZERO = "0x0000000000000000000000000000000000000000";

export function VoteWidget({
  proposalId,
  daoId,
  token,
  chainId,
}: {
  proposalId: number;
  daoId: number;
  token: string;
  chainId: number;
}) {
  const { writeContract, isPending } = useWriteContract();
  const [support, setSupport] = useState(true);
  const deployed = VOTING_ADDR !== ZERO;

  const vote = () => {
    if (!deployed) return;
    writeContract({
      address: VOTING_ADDR,
      abi: votingAbi,
      functionName: "castVote",
      args: [
        BigInt(proposalId),
        BigInt(daoId),
        (token || ZERO) as `0x${string}`,
        BigInt(chainId),
        support,
        0n,
        [],
        [],
        [],
        [],
      ],
    });
  };

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3>Vote</h3>
      {!deployed && <p className="muted">Voting contract not deployed yet.</p>}
      <div className="row" style={{ alignItems: "center" }}>
        <label style={{ margin: 0 }}>
          <input type="radio" checked={support} onChange={() => setSupport(true)} /> For
        </label>
        <label style={{ margin: 0 }}>
          <input type="radio" checked={!support} onChange={() => setSupport(false)} /> Against
        </label>
      </div>
      <button style={{ marginTop: 12 }} disabled={!deployed || isPending} onClick={vote}>
        {isPending ? "Voting…" : "Cast Vote"}
      </button>
    </div>
  );
}
