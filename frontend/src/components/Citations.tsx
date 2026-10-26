import { ExternalLink, FileText } from "lucide-react";
import type { Citation } from "../types";

export default function Citations({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
        <FileText size={13} />
        Sources
      </div>
      <ul className="space-y-1.5">
        {citations.map((c, i) => (
          <li key={`${c.source_id}-${i}`}>
            <a
              href={c.url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center justify-between gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm transition-colors hover:border-brand-300 hover:bg-brand-50"
            >
              <span className="font-medium text-ink-900">
                {c.title || c.source_name}
              </span>
              {c.url && (
                <span className="flex items-center gap-1 text-xs text-brand-600 group-hover:underline">
                  View source
                  <ExternalLink size={12} />
                </span>
              )}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
