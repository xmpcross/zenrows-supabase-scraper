import React, { useState } from 'react';
import { ModernDealCard } from '../components/ModernDealCard';

export interface PriceDropItem {
  id: string;
  title: string;
  brand: string;
  category: string;
  imageUrl: string;
  currentPrice: number;
  originalPrice: number;
  priceDropAmount: number;
  activeOffersCount: number;
  lowestMarketplace: string;
  productUrl: string;
  isAllTimeLow: boolean;
}

const SAMPLE_PRICE_DROPS: PriceDropItem[] = [
  {
    id: "drop-1",
    title: "Bose QuietComfort 45 Wireless Noise Cancelling Headphones",
    brand: "Bose",
    category: "Audio",
    imageUrl: "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=400",
    currentPrice: 189.00,
    originalPrice: 329.00,
    priceDropAmount: 140.00,
    activeOffersCount: 4,
    lowestMarketplace: "Best Buy",
    productUrl: "https://nxt.bargains/product/bose-qc45",
    isAllTimeLow: true
  },
  {
    id: "drop-2",
    title: "Google Nest Learning Thermostat 3rd Generation Stainless Steel",
    brand: "Google",
    category: "Smart Home",
    imageUrl: "https://images.unsplash.com/photo-1558002038-1055907df827?w=400",
    currentPrice: 179.00,
    originalPrice: 249.00,
    priceDropAmount: 70.00,
    activeOffersCount: 3,
    lowestMarketplace: "Walmart",
    productUrl: "https://nxt.bargains/product/nest-thermostat",
    isAllTimeLow: false
  },
  {
    id: "drop-3",
    title: "CeraVe Moisturizing Cream for Dry Skin 19 oz Tub",
    brand: "CeraVe",
    category: "Beauty & Skincare",
    imageUrl: "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
    currentPrice: 14.50,
    originalPrice: 21.99,
    priceDropAmount: 7.49,
    activeOffersCount: 4,
    lowestMarketplace: "iHerb",
    productUrl: "https://nxt.bargains/product/cerave-cream",
    isAllTimeLow: true
  }
];

export const PriceDropsPage: React.FC = () => {
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const filteredDrops = SAMPLE_PRICE_DROPS.filter(item => {
    if (activeFilter === "all_time_low") return item.isAllTimeLow;
    if (activeFilter === "huge_drop") return (item.priceDropAmount / item.originalPrice) >= 0.3;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#0B0F19] text-white py-10 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Price Drop Radar Banner */}
        <div className="bg-gradient-to-r from-emerald-950/40 via-[#121826] to-emerald-950/40 border border-emerald-500/30 rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1 text-center sm:text-left">
            <div className="flex items-center justify-center sm:justify-start gap-2">
              <span className="text-xl">📉</span>
              <h2 className="text-lg font-bold text-emerald-400">Price Drop Radar Active</h2>
            </div>
            <p className="text-xs text-gray-300">
              Tracked <span className="text-white font-bold">142 Price Drops Today</span> across Amazon, Best Buy, eBay, Walmart, Target, and Sephora. Total Saved: <span className="text-emerald-400 font-bold">$4,280</span>.
            </p>
          </div>
          <button className="bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold py-2.5 px-5 rounded-xl transition-all shadow-lg hover:shadow-emerald-500/20 whitespace-nowrap">
            🔔 Set Up Price Drop Alert
          </button>
        </div>

        {/* Header Title */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-gray-200 to-emerald-400 bg-clip-text text-transparent">
            Real-Time Price Drops & Historical Lows
          </h1>
          <p className="text-sm text-gray-400 max-w-2xl mx-auto">
            Products that recently dropped in price based on SQL price_history snapshot triggers.
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex justify-center border-b border-white/10 pb-4 gap-3">
          <button
            onClick={() => setActiveFilter("all")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeFilter === "all" ? "bg-emerald-500 text-black shadow-lg" : "bg-white/5 text-gray-400 hover:bg-white/10"
            }`}
          >
            All Price Drops ({SAMPLE_PRICE_DROPS.length})
          </button>
          <button
            onClick={() => setActiveFilter("all_time_low")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeFilter === "all_time_low" ? "bg-purple-500 text-white shadow-lg shadow-purple-500/20" : "bg-white/5 text-gray-400 hover:bg-white/10"
            }`}
          >
            🏆 All-Time Lows Only
          </button>
          <button
            onClick={() => setActiveFilter("huge_drop")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeFilter === "huge_drop" ? "bg-emerald-500 text-black shadow-lg" : "bg-white/5 text-gray-400 hover:bg-white/10"
            }`}
          >
            🔥 Huge Drops (>30% Off)
          </button>
        </div>

        {/* Price Drops Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredDrops.map((drop) => (
            <ModernDealCard
              key={drop.id}
              id={drop.id}
              title={drop.title}
              brand={drop.brand}
              category={drop.category}
              imageUrl={drop.imageUrl}
              currentPrice={drop.currentPrice}
              originalPrice={drop.originalPrice}
              activeOffersCount={drop.activeOffersCount}
              lowestMarketplace={drop.lowestMarketplace}
              productUrl={drop.productUrl}
              isAllTimeLow={drop.isAllTimeLow}
              priceDropAmount={drop.priceDropAmount}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default PriceDropsPage;
