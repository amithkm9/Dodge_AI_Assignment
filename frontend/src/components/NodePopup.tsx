"use client";

import { useEffect, useState } from "react";
import { fetchNodeDetail, NodeDetail } from "@/lib/api";

interface NodePopupProps {
  nodeId: string;
  position: { x: number; y: number };
  onClose: () => void;
  onExpand: (nodeId: string) => void;
}

const LABEL_COLORS: Record<string, string> = {
  Customer: "bg-blue-500",
  SalesOrder: "bg-indigo-500",
  SalesOrderItem: "bg-indigo-400",
  Delivery: "bg-sky-500",
  DeliveryItem: "bg-sky-400",
  BillingDocument: "bg-red-500",
  BillingItem: "bg-red-400",
  JournalEntry: "bg-amber-500",
  Payment: "bg-green-500",
  Material: "bg-cyan-500",
  Plant: "bg-violet-500",
  Address: "bg-pink-500",
};

export default function NodePopup({
  nodeId,
  position,
  onClose,
  onExpand,
}: NodePopupProps) {
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchNodeDetail(nodeId)
      .then(setDetail)
      .finally(() => setLoading(false));
  }, [nodeId]);

  const popupStyle: React.CSSProperties = {
    position: "absolute",
    left: Math.min(position.x + 15, window.innerWidth - 400),
    top: Math.max(20, Math.min(position.y - 80, window.innerHeight - 500)),
    zIndex: 1000,
  };

  const labelColor = detail ? LABEL_COLORS[detail.label] || "bg-slate-500" : "bg-slate-500";

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/5 backdrop-blur-[1px]"
        onClick={onClose}
      />

      {/* Popup Card */}
      <div
        style={popupStyle}
        className="w-[360px] bg-white rounded-xl shadow-2xl border border-slate-200/80 z-50 overflow-hidden animate-scaleIn"
      >
        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-flex items-center gap-2 text-slate-500">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-sm">Loading details...</span>
            </div>
          </div>
        ) : detail ? (
          <>
            {/* Header */}
            <div className="px-5 py-4 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${labelColor} shadow-sm`}></div>
                <h3 className="font-bold text-slate-800 text-lg">
                  {detail.label}
                </h3>
              </div>
            </div>

            {/* Properties */}
            <div className="px-5 py-4 max-h-[340px] overflow-y-auto">
              {/* Entity Type */}
              <div className="flex items-start text-sm mb-3 pb-3 border-b border-slate-100">
                <span className="text-slate-400 w-[160px] flex-shrink-0 font-medium">Entity:</span>
                <span className="text-slate-800 font-semibold">{detail.label}</span>
              </div>

              {/* All Properties */}
              <div className="space-y-2">
                {Object.entries(detail.properties).slice(0, 12).map(([key, value]) => {
                  if (value === null || value === undefined || value === "") return null;
                  const strValue = String(value);
                  const displayValue = strValue.length > 40 ? strValue.slice(0, 40) + "..." : strValue;
                  return (
                    <div key={key} className="flex items-start text-sm group">
                      <span className="text-slate-400 w-[160px] flex-shrink-0 truncate font-medium">
                        {key}:
                      </span>
                      <span className="text-slate-700 break-all group-hover:text-slate-900 transition-colors">
                        {displayValue}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Hidden fields note */}
              {Object.keys(detail.properties).length > 12 && (
                <p className="text-xs text-blue-500 italic mt-4 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  Additional fields hidden for readability
                </p>
              )}

              {/* Connections */}
              <div className="flex items-center text-sm mt-4 pt-4 border-t border-slate-100">
                <span className="text-slate-400 w-[160px] flex-shrink-0 font-medium">Connections:</span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="text-slate-800 font-semibold">{detail.neighbors?.length || 0}</span>
                  <span className="text-slate-400 text-xs">linked nodes</span>
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="px-5 py-4 bg-slate-50/80 border-t border-slate-100 flex gap-3">
              <button
                onClick={() => onExpand(nodeId)}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-all duration-200 shadow-sm hover:shadow-md active:scale-[0.98] flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
                Expand Node
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2.5 bg-white text-slate-600 text-sm font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-all duration-200 active:scale-[0.98]"
              >
                Close
              </button>
            </div>
          </>
        ) : (
          <div className="p-8 text-center">
            <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-slate-500 text-sm">No details available</p>
          </div>
        )}
      </div>
    </>
  );
}
