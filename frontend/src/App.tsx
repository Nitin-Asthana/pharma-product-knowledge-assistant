import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import ChatPage from "./pages/ChatPage";
import ProductsPage from "./pages/ProductsPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import { api } from "./services/api";
import type { Health, Stats } from "./types";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.stats().then(setStats).catch(() => setStats(null));
  }, []);

  return (
    <div className="min-h-full">
      <Header health={health} />
      <main>
        <Routes>
          <Route path="/" element={<ChatPage stats={stats} />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/products/:productId" element={<ProductDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
