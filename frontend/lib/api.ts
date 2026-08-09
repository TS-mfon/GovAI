const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function j(url: string, init?: RequestInit) {
  const r = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!r.ok) throw new Error(`request failed: ${r.status}`);
  return r.json();
}

export const listProposals = () => j(`${API}/proposals`);
export const getProposal = (id: string | number) => j(`${API}/proposals/${id}`);
export const listDaos = () => j(`${API}/daos`);
export const registerDao = (payload: object) => j(`${API}/daos`, { method: "POST", body: JSON.stringify(payload) });
export const submitProposal = (payload: object) => j(`${API}/proposals`, { method: "POST", body: JSON.stringify(payload) });
export const runAI = (id: string | number) => j(`${API}/proposals/${id}/run-ai`, { method: "POST" });
export const finalize = (id: string | number) => j(`${API}/proposals/${id}/finalize`, { method: "POST" });
