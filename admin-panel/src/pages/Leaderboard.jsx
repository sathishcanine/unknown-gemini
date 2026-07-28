import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListChecks, Target, HelpCircle, Flame, Trophy } from 'lucide-react';
import Layout from '../components/Layout';
import FilterBar from '../components/FilterBar';
import Loading from '../components/Loading';
import { useFilter } from '../context/FilterContext';
import { fetchLeaderboard } from '../lib/api';

const BOARDS = [
  {
    key: 'most_tests',
    title: 'Most Tests',
    subtitle: 'In selected period',
    icon: ListChecks,
    accent: 'bg-indigo-50 text-indigo-600',
    format: (row) => `${row.value} tests`,
    detail: (row) => `${row.questions_solved || 0} Qs · ${Math.round(row.avg_accuracy || 0)}%`,
  },
  {
    key: 'highest_accuracy',
    title: 'Highest Accuracy',
    subtitle: 'Min. 5 answers in period',
    icon: Target,
    accent: 'bg-emerald-50 text-emerald-600',
    format: (row) => `${row.value}%`,
    detail: (row) => `${row.questions_solved || 0} Qs · ${row.total_tests || 0} tests`,
  },
  {
    key: 'most_questions',
    title: 'Most Questions',
    subtitle: 'Answers in selected period',
    icon: HelpCircle,
    accent: 'bg-amber-50 text-amber-600',
    format: (row) => `${row.value} Qs`,
    detail: (row) => `${row.total_tests || 0} tests · ${Math.round(row.avg_accuracy || 0)}%`,
  },
  {
    key: 'longest_current_streak',
    title: 'Current Streak',
    subtitle: 'All-time activity days',
    icon: Flame,
    accent: 'bg-rose-50 text-rose-600',
    format: (row) => `${row.value} days`,
    detail: (row) => `Best ${row.highest_streak || 0} · ${row.active_days || 0} active days`,
  },
  {
    key: 'longest_highest_streak',
    title: 'Best Streak Ever',
    subtitle: 'All-time activity days',
    icon: Trophy,
    accent: 'bg-violet-50 text-violet-600',
    format: (row) => `${row.value} days`,
    detail: (row) => `Now ${row.current_streak || 0} · ${row.active_days || 0} active days`,
  },
];

function RankBadge({ rank }) {
  const styles =
    rank === 1
      ? 'bg-amber-100 text-amber-700'
      : rank === 2
        ? 'bg-slate-200 text-slate-700'
        : rank === 3
          ? 'bg-orange-100 text-orange-700'
          : 'bg-slate-100 text-slate-500';
  return (
    <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${styles}`}>
      {rank}
    </span>
  );
}

function BoardCard({ board, rows, onOpenUser }) {
  const Icon = board.icon;
  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${board.accent}`}>
          <Icon size={18} />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-800">{board.title}</div>
          <div className="text-[11px] text-slate-400">{board.subtitle}</div>
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-10 px-4">No data in this period yet.</p>
      ) : (
        <ul className="divide-y divide-slate-50">
          {rows.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => onOpenUser(row.id)}
                className="w-full flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition text-left"
              >
                <RankBadge rank={row.rank} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-800 truncate">{row.display_name}</div>
                  <div className="text-[11px] text-slate-400 truncate">{row.email}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-bold text-slate-800">{board.format(row)}</div>
                  <div className="text-[11px] text-slate-400">{board.detail(row)}</div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Leaderboard() {
  const { range } = useFilter();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchLeaderboard({ start: range.start, end: range.end, limit: 20 })
      .then(setData)
      .finally(() => setLoading(false));
  }, [range.start, range.end]);

  return (
    <Layout
      title="Leaderboard Analytics"
      subtitle="Most active · highest accuracy · longest streaks (from real quiz & activity data)"
    >
      <FilterBar />
      <p className="text-xs text-slate-400 mb-4 -mt-2">
        Tests / accuracy / questions use the selected date range. Streaks are all-time (IST calendar days).
      </p>

      {loading || !data ? (
        <Loading />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
          {BOARDS.map((board) => (
            <BoardCard
              key={board.key}
              board={board}
              rows={data[board.key] || []}
              onOpenUser={(id) => navigate(`/users/${id}`)}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}
