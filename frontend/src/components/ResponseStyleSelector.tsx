import type { ResponseStyle } from "../types";

const STYLES: { value: ResponseStyle; label: string }[] = [
  { value: "concise", label: "Concise" },
  { value: "standard", label: "Standard" },
  { value: "detailed", label: "Detailed" },
  { value: "executive", label: "Executive" },
];

export default function ResponseStyleSelector({
  value,
  onChange,
}: {
  value: ResponseStyle;
  onChange: (v: ResponseStyle) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
      {STYLES.map((s) => (
        <button
          key={s.value}
          onClick={() => onChange(s.value)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            value === s.value
              ? "bg-white text-brand-700 shadow-sm"
              : "text-ink-500 hover:text-ink-900"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
