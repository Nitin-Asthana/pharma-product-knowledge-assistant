import { Lightbulb } from "lucide-react";

const SUGGESTED = [
  "Tell me about DEMOCIN",
  "Compare DEMOCIN and DEMOCIN O",
  "Which products contain Nurobalin?",
  "Show anti-infective products",
  "Give me an executive portfolio overview",
];

export default function SuggestedQuestions({
  onPick,
}: {
  onPick: (q: string) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
        <Lightbulb size={13} />
        Suggested questions
      </div>
      <div className="flex flex-wrap gap-2">
        {SUGGESTED.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-ink-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
