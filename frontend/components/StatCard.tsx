export function StatCard({
  label,
  value,
  accent = "text-ink",
  sub,
}: {
  label: string;
  value: string | number;
  accent?: string;
  sub?: string;
}) {
  return (
    <div className="stat-card">
      <p className="text-sm text-ink-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold tracking-tight ${accent}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-ink-400">{sub}</p>}
    </div>
  );
}
