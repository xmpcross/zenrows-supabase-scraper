import React from 'react';

export interface DealCardProps {
  id: string;
  title: string;
  brand?: string;
  category?: string;
  imageUrl: string;
  currentPrice: number;
  originalPrice?: number;
  discountPercent?: number;
  activeOffersCount: number;
  lowestMarketplace: string;
  productUrl: string;
  isAllTimeLow?: boolean;
  priceDropAmount?: number;
}

export const ModernDealCard: React.FC<DealCardProps> = ({
  title,
  brand,
  imageUrl,
  currentPrice,
  originalPrice,
  discountPercent,
  activeOffersCount,
  lowestMarketplace,
  productUrl,
  isAllTimeLow,
  priceDropAmount
}) => {
  const calcDiscount = discountPercent || (originalPrice && originalPrice > currentPrice 
    ? Math.round(((originalPrice - currentPrice) / originalPrice) * 100) 
    : 0);

  return (
    <div className="group relative bg-[#121826]/80 backdrop-blur-md border border-white/10 rounded-2xl p-5 hover:border-emerald-500/50 transition-all duration-300 hover:shadow-[0_0_25px_rgba(16,185,129,0.15)] flex flex-col justify-between">
      {/* Top Badges Header */}
      <div className="flex justify-between items-center mb-3">
        {calcDiscount > 0 ? (
          <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1">
            <span>📉</span> {calcDiscount}% OFF
          </span>
        ) : (
          <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold px-2.5 py-1 rounded-full">
            🔥 Best Price
          </span>
        )}

        <span className="bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-medium px-2.5 py-1 rounded-full">
          {activeOffersCount} Store Prices
        </span>
      </div>

      {/* Product Image & Meta */}
      <div className="flex flex-col items-center text-center my-2">
        <div className="h-44 w-full flex items-center justify-center mb-3 overflow-hidden rounded-xl bg-white/5 p-2">
          <img 
            src={imageUrl || "/placeholder-product.png"} 
            alt={title} 
            className="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform duration-300"
            onError={(e) => { (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=300'; }}
          />
        </div>
        {brand && <span className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider">{brand}</span>}
        <h3 className="text-sm font-semibold text-white line-clamp-2 mt-1 group-hover:text-emerald-400 transition-colors leading-snug">
          {title}
        </h3>
      </div>

      {/* Price Drop Alert / All Time Low Pill */}
      {isAllTimeLow ? (
        <div className="my-2 text-[11px] text-purple-300 bg-purple-500/10 border border-purple-500/30 px-2.5 py-1 rounded-lg text-center font-medium">
          🏆 All-Time Lowest Price Ever Recorded!
        </div>
      ) : priceDropAmount && priceDropAmount > 0 ? (
        <div className="my-2 text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-lg text-center font-medium">
          📉 Price Dropped by ${priceDropAmount.toFixed(2)} in 24h
        </div>
      ) : null}

      {/* Pricing & Call to Action */}
      <div className="mt-2 pt-3 border-t border-white/5">
        <div className="flex justify-between items-baseline mb-3">
          <div>
            {originalPrice && originalPrice > currentPrice && (
              <span className="text-xs text-gray-400 line-through mr-2">${originalPrice.toFixed(2)}</span>
            )}
            <span className="text-xl font-bold text-emerald-400">${currentPrice.toFixed(2)}</span>
          </div>
          <span className="text-xs text-gray-400 capitalize">via {lowestMarketplace}</span>
        </div>

        <a
          href={productUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full inline-flex justify-center items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xs font-semibold py-2.5 px-4 rounded-xl transition-all shadow-lg hover:shadow-blue-500/25"
        >
          Compare {activeOffersCount} Offers ➔
        </a>
      </div>
    </div>
  );
};
