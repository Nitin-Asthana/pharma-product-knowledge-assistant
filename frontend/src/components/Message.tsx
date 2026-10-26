import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Sparkles, User } from "lucide-react";
import type { Citation } from "../types";
import Citations from "./Citations";

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  intent?: string;
  retrievalMode?: string;
  streaming?: boolean;
}

export default function Message({ turn }: { turn: ChatTurn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[85%] items-start gap-3">
          <div className="rounded-2xl rounded-tr-sm bg-brand-700 px-4 py-2.5 text-sm leading-relaxed text-white">
            {turn.content}
          </div>
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
            <User size={15} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex max-w-[90%] items-start gap-3">
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-700 text-white">
          <Sparkles size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-card">
            <div className="markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {turn.content || ""}
              </ReactMarkdown>
              {turn.streaming && (
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse-dot bg-brand-400 align-middle" />
              )}
            </div>
            {turn.citations && <Citations citations={turn.citations} />}
            {(turn.intent || turn.retrievalMode) && !turn.streaming && (
              <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-2.5">
                {turn.intent && <Tag>{prettify(turn.intent)}</Tag>}
                {turn.retrievalMode && <Tag>retrieval: {turn.retrievalMode}</Tag>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink-500">
      {children}
    </span>
  );
}

function prettify(intent: string): string {
  return intent.toLowerCase().replace(/_/g, " ");
}
