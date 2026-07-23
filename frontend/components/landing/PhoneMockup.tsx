export function PhoneMockup() {
  return (
    <div className="relative mx-auto w-full max-w-[320px] animate-float">
      <div className="absolute -inset-8 rounded-[3rem] bg-gradient-to-br from-ink-100 via-ink-50 to-white blur-2xl" />
      <div className="relative overflow-hidden rounded-[2.5rem] border-[10px] border-ink bg-ink shadow-phone">
        <div className="absolute left-1/2 top-3 z-10 h-6 w-24 -translate-x-1/2 rounded-full bg-ink-800" />
        <div className="aspect-[9/19] bg-white pt-10">
          <div className="border-b border-ink-100 px-5 pb-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-ink-400">
              ResumeBuild
            </p>
            <p className="mt-2 text-lg font-bold text-ink">Your matches</p>
            <p className="text-xs text-ink-500">12 roles · 8 above threshold</p>
          </div>

          <div className="space-y-3 p-4">
            {[
              { title: "Software Engineer", company: "Stripe", score: 92 },
              { title: "Backend Developer", company: "Figma", score: 87 },
              { title: "Full Stack Engineer", company: "Airbnb", score: 81 },
            ].map((job) => (
              <div
                key={job.title}
                className="rounded-2xl border border-ink-100 bg-ink-50 p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold text-ink">{job.title}</p>
                    <p className="text-[10px] text-ink-500">{job.company}</p>
                  </div>
                  <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[10px] font-bold text-white">
                    {job.score}
                  </span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-200">
                  <div
                    className="h-full rounded-full bg-ink"
                    style={{ width: `${job.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="absolute bottom-0 inset-x-0 border-t border-ink-100 bg-white p-4">
            <div className="rounded-full bg-ink py-2.5 text-center text-xs font-semibold text-white">
              Discover more jobs
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
