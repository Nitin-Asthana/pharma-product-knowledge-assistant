import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Send, Sparkles, Trash2 } from "lucide-react";
import { api, streamChat } from "../services/api";
import type { ResponseStyle, SourceStatus, Stats } from "../types";
import SourceSelector from "../components/SourceSelector";
import KnowledgeStatus from "../components/KnowledgeStatus";
import ResponseStyleSelector from "../components/ResponseStyleSelector";
import SuggestedQuestions from "../components/SuggestedQuestions";
import Message, { ChatTurn } from "../components/Message";
import StreamingStatus from "../components/StreamingStatus";

let turnCounter = 0;
const nextId = () => `t${Date.now()}-${turnCounter++}`;

// Module-scoped guard so a deep-linked prompt is handled exactly once, even
// when React StrictMode double-invokes effects in development. Product pages
// append a unique nonce so repeated clicks are still processed.
let lastHandledDeepLink = "";

export default function ChatPage({ stats }: { stats: Stats | null }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [style, setStyle] = useState<ResponseStyle>("standard");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<string>("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.sourcesStatus().then((r) => setSources(r.sources)).catch(() => setSources([]));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, stage]);

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || busy) return;

      const userTurn: ChatTurn = { id: nextId(), role: "user", content: message };
      const assistantId = nextId();
      setTurns((prev) => [
        ...prev,
        userTurn,
        { id: assistantId, role: "assistant", content: "", streaming: true },
      ]);
      setInput("");
      setBusy(true);
      setStage("Searching product knowledge...");

      try {
        await streamChat(
          {
            message,
            conversation_id: conversationId,
            response_style: style,
            source_ids: selectedSources,
          },
          {
            onStatus: (s) => setStage(s),
            onToken: (tok) => {
              setStage("");
              setTurns((prev) =>
                prev.map((t) =>
                  t.id === assistantId ? { ...t, content: t.content + tok } : t
                )
              );
            },
            onDone: (payload) => {
              setConversationId(payload.conversation_id);
              setTurns((prev) =>
                prev.map((t) =>
                  t.id === assistantId
                    ? {
                        ...t,
                        streaming: false,
                        citations: payload.citations,
                        intent: payload.intent,
                        retrievalMode: payload.retrieval_mode,
                      }
                    : t
                )
              );
            },
            onError: () => {
              setTurns((prev) =>
                prev.map((t) =>
                  t.id === assistantId
                    ? {
                        ...t,
                        streaming: false,
                        content:
                          t.content ||
                          "The assistant is temporarily unavailable. Please try again.",
                      }
                    : t
                )
              );
            },
          }
        );
      } finally {
        setBusy(false);
        setStage("");
      }
    },
    [busy, conversationId, selectedSources, style]
  );

  // Support deep-linking from product pages:
  //   /?ask=...      -> send the question immediately
  //   /?compose=...  -> prefill the input (user completes it, e.g. Compare)
  // Guarded so it runs once per navigation even under StrictMode double-invoke.
  useEffect(() => {
    const search = location.search;
    if (!search || search === lastHandledDeepLink) return;
    const params = new URLSearchParams(search);
    const ask = params.get("ask");
    const compose = params.get("compose");
    if (!ask && !compose) return;

    lastHandledDeepLink = search;
    navigate("/", { replace: true });

    if (ask) {
      send(ask);
    } else if (compose) {
      setInput(compose);
      setTimeout(() => {
        const el = inputRef.current;
        if (el) {
          el.focus();
          el.setSelectionRange(el.value.length, el.value.length);
        }
      }, 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  const empty = turns.length === 0;

  const clearChat = () => {
    setTurns([]);
    setConversationId(null);
    setInput("");
    setStage("");
  };

  return (
    <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[300px_1fr]">
      {/* Left rail */}
      <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <SourceSelector
          sources={sources}
          selected={selectedSources}
          onChange={setSelectedSources}
        />
        <KnowledgeStatus stats={stats} />
      </aside>

      {/* Conversation */}
      <section className="flex min-h-[calc(100vh-8rem)] flex-col rounded-xl border border-slate-200 bg-white shadow-card">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 className="text-sm font-semibold text-ink-900">Conversation</h2>
          <div className="flex items-center gap-2">
            <ResponseStyleSelector value={style} onChange={setStyle} />
            <button
              onClick={clearChat}
              disabled={busy || empty}
              title="Clear conversation"
              className="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-ink-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Trash2 size={14} />
              Clear
            </button>
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto px-5 py-6">
          {empty ? (
            <Welcome onPick={send} />
          ) : (
            turns.map((t) => <Message key={t.id} turn={t} />)
          )}
          {stage && <StreamingStatus stage={stage} />}
        </div>

        <div className="border-t border-slate-200 p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-end gap-2"
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              rows={1}
              placeholder="Ask about a product, composition, ingredient or category..."
              className="max-h-40 flex-1 resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm text-ink-900 outline-none placeholder:text-ink-500 focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-700 text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={18} />
            </button>
          </form>
          <p className="mt-2 text-center text-[11px] text-ink-500">
            Answers are grounded in the configured knowledge sources. The assistant
            abstains when evidence is insufficient.
          </p>
        </div>
      </section>
    </div>
  );
}

function Welcome({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl py-8 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-700 text-white">
        <Sparkles size={22} />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
        Product Knowledge Assistant
      </h1>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-500">
        Explore product information across the configured ABC Pharma knowledge
        sources — grounded, cited and source-traceable.
      </p>
      <div className="mt-8 text-left">
        <SuggestedQuestions onPick={onPick} />
      </div>
    </div>
  );
}
