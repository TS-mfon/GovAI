"use client";

import { useEffect, useState } from "react";
import { listProposals } from "@/lib/api";
import { ProposalCard } from "@/components/ProposalCard";

export default function Dashboard() {
  const [proposals, setProposals] = useState<any[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    listProposals()
      .then(setProposals)
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div>
      <h1>GovAI — Cross-DAO Governance</h1>
      <p className="muted">
        AI summaries, risk scoring, and token-weighted voting across every DAO on GovAI.
      </p>
      {err && <p className="badge risk">backend unreachable: {err}</p>}
      <div className="grid">
        {proposals.map((p) => (
          <ProposalCard key={p.id} p={p} />
        ))}
      </div>
      {!err && proposals.length === 0 && (
        <p className="muted" style={{ marginTop: 18 }}>
          No proposals yet. Onboard a DAO and submit one. The AI review runs via the backend
          relayer (POST /proposals/{"<id>"}/run-ai).
        </p>
      )}
    </div>
  );
}
