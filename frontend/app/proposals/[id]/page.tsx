"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getProposal, listDaos } from "@/lib/api";
import { ScoreGauge } from "@/components/ScoreGauge";
import { VoteWidget } from "@/components/VoteWidget";

const ZERO = "0x0000000000000000000000000000000000000000";

export default function ProposalDetail() {
  const { id } = useParams();
  const [prop, setProp] = useState<any>(null);
  const [daos, setDaos] = useState<any[]>([]);

  useEffect(() => {
    getProposal(String(id)).then(setProp).catch(() => setProp({ error: true }));
    listDaos().then(setDaos).catch(() => setDaos([]));
  }, [id]);

  if (!prop) return <p>Loading…</p>;
  if (prop.error) return <p className="badge risk">proposal not found</p>;

  const r = prop.aiReport;
  const dao = daos.find((d: any) => String(d.daoId) === String(prop.daoId)) || {};

  return (
    <div>
      <div className="stage">{prop.stage}</div>
      <h1>{prop.title || `Proposal #${prop.id}`}</h1>
      <p className="muted">
        DAO #{prop.daoId} · proposer {prop.proposer}
      </p>
      {prop.body && <p>{prop.body}</p>}

      {r ? (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>AI Review</h2>
          <p>
            {r.passed ? (
              <span className="badge safe">passed AI gate</span>
            ) : (
              <span className="badge risk">rejected</span>
            )}{" "}
            {r.reason}
          </p>
          <div className="gauge-wrap">
            <ScoreGauge value={r.riskScore} label="Risk" kind="risk" />
            <ScoreGauge value={r.benefitScore} label="Benefit" kind="benefit" />
            <ScoreGauge value={r.intentClarity} label="Intent" kind="intent" />
          </div>
          {r.selfDealing && <span className="badge risk">self-dealing flagged</span>}{" "}
          {r.malicious && <span className="badge risk">malicious flagged</span>}
          <p className="muted" style={{ marginTop: 8 }}>
            alignment confidence {r.confidence}%
          </p>
        </div>
      ) : (
        <p className="muted">
          AI review not run yet. Trigger it from the backend: POST /proposals/{String(id)}/run-ai
        </p>
      )}

      {prop.stage === "Voting" && (
        <VoteWidget
          proposalId={Number(prop.id)}
          daoId={Number(prop.daoId)}
          token={dao.token || ZERO}
          chainId={Number(dao.chainId || 0)}
        />
      )}
    </div>
  );
}
