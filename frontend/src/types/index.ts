// Shared API types mirroring the FastAPI backend contract.

export type ResponseStyle = "concise" | "standard" | "detailed" | "executive";

export interface Source {
  source_id: string;
  name: string;
  description?: string;
  url: string;
  source_type: string;
  enabled: boolean;
}

export interface SourceStatus {
  source_id: string;
  name: string;
  enabled: boolean;
  status: "ready" | "disabled" | "error" | "not_ingested";
  product_count: number;
  category_count: number;
  last_ingested_at: string;
  url: string;
  source_type: string;
  message?: string;
}

export interface Citation {
  source_id: string;
  source_name: string;
  title?: string;
  url?: string;
}

export interface Stats {
  sources: number;
  products: number;
  categories: number;
  last_refreshed: string;
  status: string;
  search_available: boolean;
  openai_available: boolean;
}

export interface Health {
  status: string;
  registry_ok: boolean;
  products: number;
  sources: number;
}

export interface ProductSummary {
  product_id: string;
  brand_name: string;
  therapeutic_category: string;
  composition: string;
  source_id: string;
  source_name: string;
  source_url: string;
}

export interface Ingredient {
  product_id: string;
  source_id: string;
  brand_name: string;
  ingredient: string;
  strength: string;
  unit: string;
  raw_composition: string;
}

export interface Product extends ProductSummary {
  source_type: string;
  source_title: string;
  raw_product_name: string;
  raw_category: string;
  raw_composition: string;
  brand_name_normalized: string;
  composition_normalized: string;
  therapeutic_category_normalized: string;
  ingredients: Ingredient[];
  scraped_at: string;
}

export interface SearchResultItem {
  product_id: string;
  brand_name: string;
  therapeutic_category: string;
  composition: string;
  source_id: string;
  source_name: string;
  source_url: string;
  score: number;
  retrieval_mode: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  products: string[];
  intent: string;
  retrieval_mode: string;
  conversation_id: string;
}
