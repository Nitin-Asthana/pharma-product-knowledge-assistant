import { Link } from "react-router-dom";
import { Tag, Database, MessageSquareText, GitCompare, Check } from "lucide-react";
import type { ProductSummary } from "../types";

interface ProductCardProps {
  product: ProductSummary;
  onAskAI?: (product: ProductSummary) => void;
  onCompare?: (product: ProductSummary) => void;
  // When in comparison mode the card becomes a selector for the second product.
  selectMode?: boolean;
  onSelect?: (product: ProductSummary) => void;
}

export default function ProductCard({
  product,
  onAskAI,
  onCompare,
  selectMode,
  onSelect,
}: ProductCardProps) {
  return (
    <div
      className={`flex flex-col rounded-xl border bg-white p-4 shadow-card transition-shadow hover:shadow-md ${
        selectMode
          ? "cursor-pointer border-brand-200 hover:border-brand-400"
          : "border-slate-200"
      }`}
      onClick={selectMode ? () => onSelect?.(product) : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        {selectMode ? (
          <span className="text-base font-semibold text-ink-900">{product.brand_name}</span>
        ) : (
          <Link
            to={`/products/${encodeURIComponent(product.product_id)}`}
            className="text-base font-semibold text-ink-900 hover:text-brand-700"
          >
            {product.brand_name}
          </Link>
        )}
      </div>

      {product.therapeutic_category && (
        <div className="mt-1.5 inline-flex w-fit items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700">
          <Tag size={11} />
          {product.therapeutic_category}
        </div>
      )}

      {product.composition && (
        <p className="mt-2.5 line-clamp-3 text-sm leading-relaxed text-ink-700">
          {product.composition}
        </p>
      )}

      <div className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-500">
        <Database size={11} />
        <span className="truncate">{product.source_name}</span>
      </div>

      <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-3">
        {selectMode ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(product);
            }}
            className="flex w-full items-center justify-center gap-1.5 rounded-md bg-brand-700 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-brand-800"
          >
            <Check size={13} />
            Select to compare
          </button>
        ) : (
          <>
            {onAskAI && (
              <button
                onClick={() => onAskAI(product)}
                className="flex items-center gap-1 rounded-md bg-brand-700 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-brand-800"
              >
                <MessageSquareText size={13} />
                Ask AI
              </button>
            )}
            <Link
              to={`/products/${encodeURIComponent(product.product_id)}`}
              className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-ink-700 hover:bg-slate-50"
            >
              View details
            </Link>
            {onCompare && (
              <button
                onClick={() => onCompare(product)}
                className="ml-auto flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-ink-700 hover:bg-slate-50"
              >
                <GitCompare size={13} />
                Compare
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
