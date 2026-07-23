export function ScoreRing({ score, passed }: { score: number; passed: boolean }) {
  return (
    <div
      className={`score-ring ${
        passed ? "border-ink bg-ink text-white" : "border-ink-300 bg-white text-ink-500"
      }`}
    >
      {Math.round(score)}
    </div>
  );
}
