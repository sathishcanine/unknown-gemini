import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function StatCard({ label, value, delta, suffix = '', icon: Icon, accent = 'indigo' }) {
  const accentMap = {
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    rose: 'bg-rose-50 text-rose-600',
    slate: 'bg-slate-100 text-slate-500',
  };

  let deltaColor = 'text-slate-400';
  let DeltaIcon = Minus;
  if (delta !== null && delta !== undefined) {
    if (delta > 0) {
      deltaColor = 'text-emerald-600';
      DeltaIcon = TrendingUp;
    } else if (delta < 0) {
      deltaColor = 'text-rose-600';
      DeltaIcon = TrendingDown;
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
        {Icon && (
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${accentMap[accent]}`}>
            <Icon size={16} />
          </div>
        )}
      </div>
      <div className="flex items-end justify-between">
        <span className="text-2xl font-bold text-slate-900">
          {value === null || value === undefined ? '\u2014' : `${value}${suffix}`}
        </span>
        {delta !== null && delta !== undefined && (
          <span className={`flex items-center gap-0.5 text-xs font-semibold ${deltaColor}`}>
            <DeltaIcon size={13} />
            {delta === 0 ? '0%' : `${Math.abs(delta)}%`}
          </span>
        )}
      </div>
    </div>
  );
}
