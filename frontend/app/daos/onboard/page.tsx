"use client";

import { useState } from "react";
import { registerDao } from "@/lib/api";

export default function OnboardDao() {
  const [form, setForm] = useState({
    name: "",
    mission: "",
    constitution: "",
    token: "0x0000000000000000000000000000000000000000",
    chainId: 0,
    maxRisk: 60,
    minBenefit: 40,
    minConfidence: 60,
    votingDuration: 3 * 24 * 3600,
    quorumBps: 4000,
    delegationOn: true,
  });
  const [result, setResult] = useState<string>("");

  const submit = async () => {
    try {
      const r = await registerDao(form);
      setResult(`DAO registered — id ${r.daoId}`);
    } catch (e) {
      setResult("error: " + String(e));
    }
  };

  return (
    <div style={{ maxWidth: 620 }}>
      <h1>Onboard your DAO</h1>
      <p className="muted">
        Permissionless. Set your constitution, token (optional), and the AI-gate thresholds
        GenLayer will enforce.
      </p>
      <label>Name</label>
      <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      <label>Mission</label>
      <textarea
        rows={2}
        value={form.mission}
        onChange={(e) => setForm({ ...form, mission: e.target.value })}
      />
      <label>Constitution (text)</label>
      <textarea
        rows={6}
        value={form.constitution}
        onChange={(e) => setForm({ ...form, constitution: e.target.value })}
      />
      <label>Token address (optional — leave zero for 1-address-1-vote)</label>
      <input value={form.token} onChange={(e) => setForm({ ...form, token: e.target.value })} />
      <label>Token chainId (0 if no token)</label>
      <input
        type="number"
        value={form.chainId}
        onChange={(e) => setForm({ ...form, chainId: Number(e.target.value) })}
      />
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>Max risk (0-100)</label>
          <input
            type="number"
            value={form.maxRisk}
            onChange={(e) => setForm({ ...form, maxRisk: Number(e.target.value) })}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label>Min benefit (0-100)</label>
          <input
            type="number"
            value={form.minBenefit}
            onChange={(e) => setForm({ ...form, minBenefit: Number(e.target.value) })}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label>Min confidence (0-100)</label>
          <input
            type="number"
            value={form.minConfidence}
            onChange={(e) => setForm({ ...form, minConfidence: Number(e.target.value) })}
          />
        </div>
      </div>
      <button style={{ marginTop: 16 }} onClick={submit}>
        Register DAO
      </button>
      {result && <p style={{ marginTop: 12 }}>{result}</p>}
    </div>
  );
}
