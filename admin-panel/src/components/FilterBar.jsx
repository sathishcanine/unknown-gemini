import { Calendar, ChevronDown, GitCompare } from 'lucide-react';
import { useState } from 'react';
import { PRESETS } from '../lib/dateRanges';
import { useFilter } from '../context/FilterContext';

export default function FilterBar() {
  const {
    preset,
    setPreset,
    customStart,
    setCustomStart,
    customEnd,
    setCustomEnd,
    compareEnabled,
    setCompareEnabled,
    range,
  } = useFilter();
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-3 mb-6">
      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:border-slate-300 shadow-sm transition"
        >
          <Calendar size={16} className="text-indigo-500" />
          {range.label}
          <ChevronDown size={14} className={`text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>

        {open && (
          <div className="absolute z-20 mt-2 w-64 bg-white border border-slate-200 rounded-xl shadow-lg p-2">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setPreset(p.id);
                  if (p.id !== 'custom') setOpen(false);
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                  preset === p.id ? 'bg-indigo-50 text-indigo-600 font-semibold' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {p.label}
              </button>
            ))}
            {preset === 'custom' && (
              <div className="p-2 flex flex-col gap-2 border-t border-slate-100 mt-1">
                <input
                  type="date"
                  value={customStart || ''}
                  onChange={(e) => setCustomStart(e.target.value)}
                  className="text-sm border border-slate-200 rounded-lg px-2 py-1.5"
                />
                <input
                  type="date"
                  value={customEnd || ''}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  className="text-sm border border-slate-200 rounded-lg px-2 py-1.5"
                />
                <button
                  onClick={() => setOpen(false)}
                  className="bg-indigo-600 text-white text-sm font-medium rounded-lg py-1.5 hover:bg-indigo-700"
                >
                  Apply
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <button
        onClick={() => setCompareEnabled(!compareEnabled)}
        disabled={preset === 'custom'}
        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed ${
          compareEnabled
            ? 'bg-indigo-600 text-white border-indigo-600'
            : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
        }`}
      >
        <GitCompare size={16} />
        Compare to previous period
      </button>

      <span className="text-xs text-slate-400 ml-1">{range.start} &rarr; {range.end}</span>
    </div>
  );
}
