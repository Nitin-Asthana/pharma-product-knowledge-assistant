import { NavLink } from "react-router-dom";
import { Boxes, MessageSquareText, Activity } from "lucide-react";
import type { Health } from "../types";

interface HeaderProps {
  health: Health | null;
}

export default function Header({ health }: HeaderProps) {
  const ready = health?.status === "ready";
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <NavLink to="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-700 text-sm font-bold tracking-tight text-white">
            W
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-[0.18em] text-brand-800">
              ABC PHARMA
            </div>
            <div className="text-[11px] font-medium text-ink-500">
              Product Knowledge Assistant
            </div>
          </div>
        </NavLink>

        <nav className="flex items-center gap-1">
          <HeaderLink to="/" icon={<MessageSquareText size={16} />} label="Assistant" end />
          <HeaderLink to="/products" icon={<Boxes size={16} />} label="Products" />
        </nav>

        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              ready ? "bg-emerald-500 animate-pulse-dot" : "bg-amber-500"
            }`}
          />
          <span className="text-xs font-medium text-ink-700">
            {ready ? "Knowledge Base Ready" : "Knowledge Base Degraded"}
          </span>
          <Activity size={13} className="text-ink-500" />
        </div>
      </div>
    </header>
  );
}

function HeaderLink({
  to,
  icon,
  label,
  end,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          isActive
            ? "bg-brand-50 text-brand-700"
            : "text-ink-500 hover:bg-slate-100 hover:text-ink-900"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
