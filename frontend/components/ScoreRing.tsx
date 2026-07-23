export function ScoreRing({ score, passed }: { score: number; passed: boolean }) {
  const color = passed ? "border-emerald-500/60 text-emerald-300" : "border-rose-500/40 text-rose-300";
  const bg = passed ? "from-emerald-500/10" : "from-rose-500/10";

  return (
    <div className={`score-ring border-current bg-gradient-to-b ${bg} to-transparent ${color}`}>
      {Math.round(score)}
    </div>
  );
}
