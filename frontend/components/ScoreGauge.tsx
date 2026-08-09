export function ScoreGauge({
  value,
  label,
  kind,
}: {
  value: number;
  label: string;
  kind: "risk" | "benefit" | "intent";
}) {
  const v = Math.max(0, Math.min(100, value));
  const pct = v / 100;
  const color =
    kind === "risk"
      ? v > 60
        ? "var(--bad)"
        : v > 30
        ? "var(--warn)"
        : "var(--good)"
      : v >= 60
      ? "var(--good)"
      : v >= 40
      ? "var(--warn)"
      : "var(--bad)";
  const r = 40;
  const circ = Math.PI * r;
  const dash = circ * pct;

  return (
    <div style={{ textAlign: "center" }}>
      <svg width="100" height="60" viewBox="0 0 100 60">
        <path d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke="var(--border)" strokeWidth="8" />
        <path
          d="M10 50 A40 40 0 0 1 90 50"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
        />
        <text x="50" y="48" textAnchor="middle" fontSize="16" fill="var(--text)">
          {v}
        </text>
      </svg>
      <div className="muted">{label}</div>
    </div>
  );
}
