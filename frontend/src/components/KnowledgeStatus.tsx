import { Boxes, Layers, FolderTree, Clock } from "lucide-react";
import type { Stats } from "../types";

export default function KnowledgeStatus({ stats }: { stats: Stats | null }) {
  const items = [
    { icon: <Database />, label: "Sources", value: stats?.sources ?? "—" },
    { icon: <Boxes />, label: "Products", value: stats?.products ?? "—" },
    { icon: <FolderTree />, label: "Categories", value: stats?.categories ?? "—" },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="mb-3 flex items-center gap-2">
        <Layers size={15} className="text-brand-600" />
        <h3 className="text-sm font-semibold text-ink-900">Knowledge Base</h3>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {items.map((it) => (
          <div
            key={it.label}
            className="rounded-lg border border-slate-100 bg-slate-50 px-2 py-3 text-center"
          >
            <div className="text-lg font-semibold text-ink-900">{it.value}</div>
            <div className="text-[11px] font-medium text-ink-500">{it.label}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-1.5 border-t border-slate-100 pt-3 text-[11px] text-ink-500">
        <Clock size={12} />
        <span>
          Last refreshed:{" "}
          {stats?.last_refreshed ? formatDate(stats.last_refreshed) : "—"}
        </span>
      </div>
      <div className="mt-1.5 flex items-center gap-1.5 text-[11px]">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            (stats?.products ?? 0) > 0 ? "bg-emerald-500" : "bg-amber-500"
          }`}
        />
        <span className="text-ink-500">
          Status: {(stats?.products ?? 0) > 0 ? "Ready" : "Not ingested"}
        </span>
      </div>
    </div>
  );
}

// Small inline Database icon to avoid an extra import name clash.
function Database() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14a9 3 0 0 0 18 0V5" />
    </svg>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
