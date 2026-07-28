import { Sparkles } from 'lucide-react';

export default function ComingSoon({ title, description }) {
  return (
    <div className="bg-white border border-dashed border-slate-300 rounded-2xl p-16 flex flex-col items-center text-center">
      <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-500 flex items-center justify-center mb-4">
        <Sparkles size={26} />
      </div>
      <h3 className="text-lg font-bold text-slate-800 mb-2">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md">{description}</p>
    </div>
  );
}
