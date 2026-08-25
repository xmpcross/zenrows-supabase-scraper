import React, { useState } from 'react';
import { ModernDealCard } from '../components/ModernDealCard';

export interface DealItem {
  id: string;
  title: string;
  brand: string;
  category: string;
  imageUrl: string;
  currentPrice: number;
  originalPrice: number;
  activeOffersCount: number;
  lowestMarketplace: string;
  productUrl: string;
}

const SAMPLE_DEALS: DealItem[] = [
  {
    id: "deal-1",
    title: "Roborock S8 Pro Ultra Robot Vacuum and Mop Combo",
    brand: "Roborock",
    category: "Smart Home",
    imageUrl: "https://images.unsplash.com/photo-1589923188900-85dae523342b?w=400",
    currentPrice: 1039.99,
    originalPrice: 1599.99,
    activeOffersCount: 4,
    lowestMarketplace: "Amazon",
    productUrl: "https://nxt.bargains/product/roborock-s8"
  },
  {
    id: "deal-2",
    title: "Ring Video Doorbell 4 (2024 Release) with 1080p HD Video",
    brand: "Ring",
    category: "Security",
    imageUrl: "https://images.unsplash.com/photo-1558002038-1055907df827?w=400",
    currentPrice: 129.99,
    originalPrice: 219.99,
    activeOffersCount: 3,
    lowestMarketplace: "Best Buy",
    productUrl: "https://nxt.bargains/product/ring-doorbell-4"
  },
  {
    id: "deal-3",
    title: "The Ordinary Niacinamide 10% + Zinc 1% High-Strength Serum",
    brand: "The Ordinary",
    category: "Beauty & Skincare",
    imageUrl: "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
    currentPrice: 6.00,
    originalPrice: 12.00,
    activeOffersCount: 5,
    lowestMarketplace: "Sephora",
    productUrl: "https://nxt.bargains/product/the-ordinary-niacinamide"
  },
  {
    id: "deal-4",
    title: "Dyson V15 Detect Cordless Vacuum Cleaner",
    brand: "Dyson",
    category: "Smart Home",
    imageUrl: "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?w=400",
    currentPrice: 539.99,
    originalPrice: 749.99,
    activeOffersCount: 3,
    lowestMarketplace: "eBay",
    productUrl: "https://nxt.bargains/product/dyson-v15"
  }
];

export const BestDealsPage: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>("All Deals");

  const categories = ["All Deals", "Smart Home", "Security", "Beauty & Skincare", "Tech & Audio"];

  const filteredDeals = selectedCategory === "All Deals" 
    ? SAMPLE_DEALS 
    : SAMPLE_DEALS.filter(d => d.category === selectedCategory);

  const heroDeal = SAMPLE_DEALS[0];

  return (
    <div className="min-h-screen bg-[#0B0F19] text-white py-10 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Live Deal Ticker */}
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-2.5 flex items-center justify-between text-xs text-emerald-400 font-medium">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span>⚡ 330 Verified Multi-Store Deals Live Right Now</span>
          </div>
          <span className="text-gray-400 hidden sm:inline">Auto-Refreshed via ZenRows & DataForSEO</span>
        </div>

        {/* Header Title */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-gray-200 to-emerald-400 bg-clip-text text-transparent">
            Today's Best Daily Deals & Price Comparisons
          </h1>
          <p className="text-sm text-gray-400 max-w-2xl mx-auto">
            Real-time price comparisons across Amazon, eBay, Best Buy, Target, Walmart, and Sephora. Enforcing the 3+ verified offer rule.
          </p>
        </div>

        {/* Hero Spotlight Deal */}
        {heroDeal && (
          <div className="relative bg-gradient-to-r from-[#121826] via-[#1A2234] to-[#121826] border border-emerald-500/30 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden">
            <div className="absolute top-4 left-4 bg-emerald-500 text-black text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full shadow-lg">
              🔥 Deal of the Day
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center mt-4">
              <div className="lg:col-span-5 flex justify-center">
                <img src={heroDeal.imageUrl} alt={heroDeal.title} className="max-h-64 object-contain rounded-2xl" />
              </div>
              <div className="lg:col-span-7 space-y-4 text-left">
                <span className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">{heroDeal.brand} • {heroDeal.category}</span>
                <h2 className="text-xl sm:text-2xl font-bold text-white leading-tight">{heroDeal.title}</h2>
                
                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-extrabold text-emerald-400">${heroDeal.currentPrice.toFixed(2)}</span>
                  <span className="text-lg text-gray-400 line-through">${heroDeal.originalPrice.toFixed(2)}</span>
                  <span className="bg-emerald-500/20 text-emerald-300 text-xs font-bold px-2.5 py-1 rounded-md">
                    Save ${(heroDeal.originalPrice - heroDeal.currentPrice).toFixed(2)} (-35%)
                  </span>
                </div>

                <p className="text-xs text-gray-400">
                  Verified 3+ store deals available across Amazon, Best Buy, Target, and eBay.
                </p>

                <a 
                  href={heroDeal.productUrl} 
                  className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold py-3 px-6 rounded-xl transition-all shadow-lg hover:shadow-emerald-500/20"
                >
                  Compare All 4 Retailer Prices ➔
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4 overflow-x-auto gap-2">
          <div className="flex gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-4 py-2 rounded-xl text-xs font-medium transition-all whitespace-nowrap ${
                  selectedCategory === cat 
                    ? 'bg-emerald-500 text-black font-bold shadow-lg shadow-emerald-500/20' 
                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Deal Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredDeals.map((deal) => (
            <ModernDealCard
              key={deal.id}
              id={deal.id}
              title={deal.title}
              brand={deal.brand}
              category={deal.category}
              imageUrl={deal.imageUrl}
              currentPrice={deal.currentPrice}
              originalPrice={deal.originalPrice}
              activeOffersCount={deal.activeOffersCount}
              lowestMarketplace={deal.lowestMarketplace}
              productUrl={deal.productUrl}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default BestDealsPage;
