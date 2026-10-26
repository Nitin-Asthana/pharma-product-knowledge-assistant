import { Loader2, Search } from "lucide-react";

// Non-reasoning progress indicator shown while the SSE stream is working.
// It only surfaces coarse stages (never chain-of-thought).
export default function StreamingStatus({ stage }: { stage: string }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-700 text-white">
          <Search size={15} />
        </div>
        <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-ink-500 shadow-card">
          <Loader2 size={14} className="animate-spin text-brand-600" />
          {stage}
        </div>
      </div>
    </div>
  );
}
