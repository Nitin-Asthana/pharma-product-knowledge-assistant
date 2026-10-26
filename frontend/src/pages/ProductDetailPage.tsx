import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Tag,
  Database,
  ExternalLink,
  MessageSquareText,
  GitCompare,
  FlaskConical,
} from "lucide-react";
import { api } from "../services/api";
import type { Product } from "../types";

export default function ProductDetailPage() {
  const { productId = "" } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api
      .product(productId)
      .then(setProduct)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) {
    return <div className="py-20 text-center text-sm text-ink-500">Loading product…</div>;
  }

  if (error || !product) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="text-sm text-ink-500">Product not found.</p>
        <Link to="/products" className="mt-3 inline-block text-sm text-brand-600 hover:underline">
          Back to Product Explorer
        </Link>
      </div>
    );
  }

  const parsedIngredients = product.ingredients.filter((i) => i.ingredient);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <Link
        to="/products"
        className="mb-4 inline-flex items-center gap-1 text-sm text-ink-500 hover:text-ink-900"
      >
        <ArrowLeft size={15} /> Product Explorer
      </Link>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
              {product.brand_name}
            </h1>
            {product.therapeutic_category && (
              <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
                <Tag size={12} />
                {product.therapeutic_category}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() =>
                navigate(
                  `/?ask=${encodeURIComponent(`Tell me about ${product.brand_name}`)}&t=${Date.now()}`
                )
              }
              className="flex items-center gap-1.5 rounded-lg bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
            >
              <MessageSquareText size={15} /> Ask AI
            </button>
            <button
              onClick={() =>
                navigate(
                  `/products?cmpId=${encodeURIComponent(product.product_id)}&cmpName=${encodeURIComponent(product.brand_name)}`
                )
              }
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-ink-700 hover:bg-slate-50"
            >
              <GitCompare size={15} /> Compare
            </button>
          </div>
        </div>

        <Section title="Composition">
          {product.composition ? (
            <p className="text-sm leading-relaxed text-ink-700">{product.composition}</p>
          ) : (
            <p className="text-sm italic text-ink-500">
              No composition available in the source for this product.
            </p>
          )}
        </Section>

        {parsedIngredients.length > 0 && (
          <Section title="Parsed ingredients">
            <div className="overflow-hidden rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-ink-500">
                  <tr>
                    <th className="px-3 py-2">
                      <span className="flex items-center gap-1">
                        <FlaskConical size={12} /> Ingredient
                      </span>
                    </th>
                    <th className="px-3 py-2">Strength</th>
                    <th className="px-3 py-2">Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {parsedIngredients.map((ing, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-ink-900">{ing.ingredient}</td>
                      <td className="px-3 py-2 text-ink-700">{ing.strength || "—"}</td>
                      <td className="px-3 py-2 text-ink-700">{ing.unit || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[11px] text-ink-500">
              Ingredients are best-effort structured extractions from the source
              composition text. The raw composition above is authoritative.
            </p>
          </Section>
        )}

        <Section title="Source">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center gap-2 text-sm text-ink-700">
              <Database size={15} className="text-brand-600" />
              <span className="font-medium text-ink-900">{product.source_name}</span>
            </div>
            {product.source_url && (
              <a
                href={product.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-brand-600 hover:underline"
              >
                View source <ExternalLink size={13} />
              </a>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-6 border-t border-slate-100 pt-5">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
        {title}
      </h2>
      {children}
    </div>
  );
}
