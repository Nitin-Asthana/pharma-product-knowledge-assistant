import { Database, CheckCircle2, XCircle, AlertTriangle, Circle } from "lucide-react";
import type { SourceStatus } from "../types";

interface SourceSelectorProps {
  sources: SourceStatus[];
  selected: string[];
  onChange: (ids: string[]) => void;
}

// Renders the dynamic knowledge-source selector. "All Sources" clears the
// filter (empty array => backend searches all enabled sources). Individual
// sources can be toggled. Nothing is hardcoded — everything derives from
// /api/sources/status.
export default function SourceSelector({
  sources,
  selected,
  onChange,
}: SourceSelectorProps) {
  const allSelected = selected.length === 0;

  const toggle = (id: string) => {
    if (selected.includes(id)) onChange(selected.filter((s) => s !== id));
    else onChange([...selected, id]);
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="mb-3 flex items-center gap-2">
        <Database size={15} className="text-brand-600" />
        <h3 className="text-sm font-semibold text-ink-900">Knowledge Sources</h3>
      </div>

      <button
        onClick={() => onChange([])}
        className={`mb-2 flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
          allSelected
            ? "border-brand-300 bg-brand-50 text-brand-800"
            : "border-slate-200 hover:bg-slate-50"
        }`}
      >
        <span className="font-medium">All Sources</span>
        {allSelected && <CheckCircle2 size={16} className="text-brand-600" />}
      </button>

      <div className="space-y-1.5">
        {sources.map((s) => {
          const active = selected.includes(s.source_id);
          return (
            <button
              key={s.source_id}
              onClick={() => toggle(s.source_id)}
              disabled={!s.enabled}
              className={`flex w-full items-start justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-colors disabled:opacity-60 ${
                active
                  ? "border-brand-300 bg-brand-50"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <StatusIcon status={s.status} />
                  <span className="truncate text-sm font-medium text-ink-900">
                    {s.name}
                  </span>
                </div>
                <div className="mt-0.5 text-[11px] text-ink-500">
                  {s.product_count} products · {s.category_count} categories
                </div>
              </div>
              {active && <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-brand-600" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: SourceStatus["status"] }) {
  switch (status) {
    case "ready":
      return <CheckCircle2 size={13} className="text-emerald-500" />;
    case "error":
      return <XCircle size={13} className="text-rose-500" />;
    case "disabled":
      return <Circle size={13} className="text-ink-300" />;
    default:
      return <AlertTriangle size={13} className="text-amber-500" />;
  }
}
