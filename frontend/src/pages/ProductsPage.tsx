import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Search, X, GitCompare } from "lucide-react";
import { api } from "../services/api";
import type { ProductSummary, SourceStatus } from "../types";
import ProductCard from "../components/ProductCard";

// Module-scoped cache so Product Explorer filters/search survive navigating
// into a product detail page and back (they reset only on a full page reload).
const explorerFilters = { q: "", sourceId: "", category: "", ingredient: "" };

export default function ProductsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [categories, setCategories] = useState<
    { therapeutic_category: string; product_count: number }[]
  >([]);
  const [ingredients, setIngredients] = useState<string[]>([]);

  const [q, setQ] = useState(explorerFilters.q);
  const [sourceId, setSourceId] = useState(explorerFilters.sourceId);
  const [category, setCategory] = useState(explorerFilters.category);
  const [ingredient, setIngredient] = useState(explorerFilters.ingredient);
  const [loading, setLoading] = useState(false);

  // Comparison mode: product 1 is pinned via URL params; the catalogue becomes
  // a selector for product 2. Picking product 2 opens the assistant with the
  // comparison question prefilled (the user presses Enter, or edits first).
  const compareId = searchParams.get("cmpId") || "";
  const compareName = searchParams.get("cmpName") || "";
  const compareMode = Boolean(compareId);

  // Keep the module cache in sync so a return visit restores the same view.
  useEffect(() => {
    explorerFilters.q = q;
    explorerFilters.sourceId = sourceId;
    explorerFilters.category = category;
    explorerFilters.ingredient = ingredient;
  }, [q, sourceId, category, ingredient]);

  useEffect(() => {
    api.sourcesStatus().then((r) => setSources(r.sources)).catch(() => {});
  }, []);

  useEffect(() => {
    api.categories(sourceId || undefined).then((r) => setCategories(r.categories)).catch(() => {});
    api.ingredients(sourceId || undefined).then((r) => setIngredients(r.ingredients)).catch(() => {});
  }, [sourceId]);

  useEffect(() => {
    setLoading(true);
    api
      .products({
        source_id: sourceId || undefined,
        category: category || undefined,
        ingredient: ingredient || undefined,
        q: q || undefined,
      })
      .then((r) => setProducts(r.products))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [sourceId, category, ingredient, q]);

  const hasFilters = useMemo(
    () => Boolean(q || sourceId || category || ingredient),
    [q, sourceId, category, ingredient]
  );

  const clear = () => {
    setQ("");
    setSourceId("");
    setCategory("");
    setIngredient("");
  };

  const askAI = (p: ProductSummary) =>
    navigate(`/?ask=${encodeURIComponent(`Tell me about ${p.brand_name}`)}&t=${Date.now()}`);

  // Enter comparison mode with this product pinned as product 1.
  const compare = (p: ProductSummary) => {
    setSearchParams({ cmpId: p.product_id, cmpName: p.brand_name });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const cancelCompare = () => setSearchParams({});

  // Product 2 chosen -> open the assistant with the full comparison prefilled.
  const selectSecond = (p: ProductSummary) => {
    const question = `Compare ${compareName} and ${p.brand_name}`;
    navigate(`/?compose=${encodeURIComponent(question)}&t=${Date.now()}`);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-ink-900">Product Explorer</h1>
        <p className="mt-1 text-sm text-ink-500">
          Browse the catalogue across the configured knowledge sources.
          {" "}
          {products.length} product{products.length === 1 ? "" : "s"} shown.
        </p>
      </div>

      {compareMode && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-ink-900">
            <GitCompare size={16} className="text-brand-600" />
            <span>
              Comparing <span className="font-semibold text-brand-700">{compareName}</span> —
              select a second product to compare.
            </span>
          </div>
          <button
            onClick={cancelCompare}
            className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-slate-50"
          >
            <X size={12} /> Cancel
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="mb-5 grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-card md:grid-cols-4">
        <div className="relative md:col-span-1">
          <Search size={15} className="absolute left-3 top-2.5 text-ink-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search brand name..."
            className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <Select label="All sources" value={sourceId} onChange={setSourceId}
          options={sources.map((s) => ({ value: s.source_id, label: s.name }))} />
        <Select label="All categories" value={category} onChange={setCategory}
          options={categories.map((c) => ({
            value: c.therapeutic_category,
            label: `${c.therapeutic_category} (${c.product_count})`,
          }))} />
        <Select label="All ingredients" value={ingredient} onChange={setIngredient}
          options={ingredients.map((i) => ({ value: i, label: i }))} />
      </div>

      {hasFilters && (
        <button
          onClick={clear}
          className="mb-4 inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-slate-50"
        >
          <X size={12} /> Clear filters
        </button>
      )}

      {loading ? (
        <div className="py-16 text-center text-sm text-ink-500">Loading products…</div>
      ) : products.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-ink-500">
          No products match the current filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products
            .filter((p) => !compareMode || p.product_id !== compareId)
            .map((p) => (
              <ProductCard
                key={p.product_id}
                product={p}
                onAskAI={askAI}
                onCompare={compare}
                selectMode={compareMode}
                onSelect={selectSecond}
              />
            ))}
        </div>
      )}
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-ink-700 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
    >
      <option value="">{label}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
