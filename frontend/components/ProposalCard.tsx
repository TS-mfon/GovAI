import Link from "next/link";

export function ProposalCard({ p }: { p: any }) {
  return (
    <div className="card">
      <div className="stage">{p.stage}</div>
      <h3>
        <Link href={`/proposals/${p.id}`}>{p.title || "(untitled proposal)"}</Link>
      </h3>
      <div className="muted">{p.daoName}</div>
      <p>{p.summary}</p>
      {p.riskScore != null && (
        <span className={`badge ${p.riskScore > 60 ? "risk" : "safe"}`}>risk {p.riskScore}</span>
      )}
      {p.selfDealing && <span className="badge risk">self-dealing</span>}
      {p.malicious && <span className="badge risk">malicious</span>}
    </div>
  );
}
