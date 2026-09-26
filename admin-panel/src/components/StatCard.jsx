import { TrendingUp, TrendingDown, Minus, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function StatCard({
  label,
  value,
  delta,
  suffix = '',
  prefix = '',
  icon: Icon,
  accent = 'indigo',
  to = null,
  hint = null,
  onClick = null,
}) {
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

  const clickable = Boolean(to || onClick);
  const className = `bg-white border border-slate-200 rounded-2xl p-5 shadow-sm text-left w-full transition ${
    clickable
      ? 'hover:border-indigo-300 hover:shadow-md hover:-translate-y-0.5 cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500'
      : ''
  }`;

  const body = (
    <>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
        <div className="flex items-center gap-1">
          {Icon && (
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${accentMap[accent]}`}>
              <Icon size={16} />
            </div>
          )}
          {clickable && <ChevronRight size={16} className="text-slate-300" />}
        </div>
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className="text-2xl font-bold text-slate-900">
          {value === null || value === undefined ? '\u2014' : `${prefix}${value}${suffix}`}
        </span>
        {delta !== null && delta !== undefined && (
          <span className={`flex items-center gap-0.5 text-xs font-semibold ${deltaColor}`}>
            <DeltaIcon size={13} />
            {delta === 0 ? '0%' : `${Math.abs(delta)}%`}
          </span>
        )}
      </div>
      {hint && <p className="mt-2 text-[11px] text-slate-400 leading-snug">{hint}</p>}
      {clickable && !hint && (
        <p className="mt-2 text-[11px] text-indigo-500 font-medium">Click to explore</p>
      )}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={className}>
        {body}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {body}
      </button>
    );
  }

  return <div className={className}>{body}</div>;
}
