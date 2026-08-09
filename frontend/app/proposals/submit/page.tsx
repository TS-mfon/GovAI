"use client";

import { useEffect, useState } from "react";
import { listDaos, submitProposal } from "@/lib/api";

export default function SubmitProposal() {
  const [daos, setDaos] = useState<any[]>([]);
  const [daoId, setDaoId] = useState<number>(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [result, setResult] = useState("");

  useEffect(() => {
    listDaos().then(setDaos).catch(() => setDaos([]));
  }, []);

  const submit = async () => {
    try {
      const r = await submitProposal({ daoId, title, body });
      setResult(`Submitted — proposal #${r.proposalId}. Run the AI review from the backend.`);
    } catch (e) {
      setResult("error: " + String(e));
    }
  };

  return (
    <div style={{ maxWidth: 620 }}>
      <h1>Submit a proposal</h1>
      <label>DAO</label>
      <select value={daoId} onChange={(e) => setDaoId(Number(e.target.value))}>
        <option value={0}>— select —</option>
        {daos.map((d) => (
          <option key={d.daoId} value={d.daoId}>
            {d.name} (#{d.daoId})
          </option>
        ))}
      </select>
      <label>Title</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} />
      <label>Body</label>
      <textarea rows={8} value={body} onChange={(e) => setBody(e.target.value)} />
      <button style={{ marginTop: 16 }} disabled={!daoId} onClick={submit}>
        Submit
      </button>
      {result && <p style={{ marginTop: 12 }}>{result}</p>}
    </div>
  );
}
