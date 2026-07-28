import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Smartphone, Globe } from 'lucide-react';
import Layout from '../components/Layout';
import FilterBar from '../components/FilterBar';
import Loading from '../components/Loading';
import { useFilter } from '../context/FilterContext';
import { fetchUsers } from '../lib/api';
import { formatISTDate, timeAgoIST } from '../lib/formatTime';

const SORT_OPTIONS = [
  { id: 'last_active_at', label: 'Last Active' },
  { id: 'created_at', label: 'Joined Date' },
  { id: 'total_tests', label: 'Total Tests' },
  { id: 'avg_accuracy', label: 'Accuracy' },
  { id: 'total_points', label: 'Points' },
];

export default function Users() {
  const { range } = useFilter();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('last_active_at');
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    fetchUsers({ start: range.start, end: range.end, search: search || undefined, sort_by: sortBy, page, page_size: 20 })
      .then(setData)
      .finally(() => setLoading(false));
  }, [range.start, range.end, search, sortBy, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <Layout title="Users" subtitle="Every student. Search, sort, and drill into individual activity.">
      <FilterBar />

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            placeholder="Search by name or email..."
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              Sort: {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        {loading || !data ? (
          <Loading />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase tracking-wide">
                <th className="text-left font-semibold px-5 py-3">Student</th>
                <th className="text-left font-semibold px-5 py-3">Joined</th>
                <th className="text-left font-semibold px-5 py-3">Last Active</th>
                <th className="text-left font-semibold px-5 py-3">Device</th>
                <th className="text-right font-semibold px-5 py-3">Tests</th>
                <th className="text-right font-semibold px-5 py-3">Accuracy</th>
                <th className="text-right font-semibold px-5 py-3">Points</th>
              </tr>
            </thead>
            <tbody>
              {data.users.map((u) => (
                <tr
                  key={u.id}
                  onClick={() => navigate(`/users/${u.id}`)}
                  className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition"
                >
                  <td className="px-5 py-3">
                    <div className="font-semibold text-slate-800">{u.display_name || 'Unnamed'}</div>
                    <div className="text-xs text-slate-400">{u.email}</div>
                  </td>
                  <td className="px-5 py-3 text-slate-500">
                    {formatISTDate(u.created_at)}
                  </td>
                  <td className="px-5 py-3 text-slate-500">{timeAgoIST(u.last_active_at)}</td>
                  <td className="px-5 py-3 text-slate-500">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-xs">
                        <Smartphone size={13} /> {u.platform || '\u2014'}
                      </span>
                      <span className="flex items-center gap-1 text-xs">
                        <Globe size={13} /> {u.country || '\u2014'}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-slate-700">{u.total_tests}</td>
                  <td className="px-5 py-3 text-right font-semibold text-slate-700">{u.avg_accuracy}%</td>
                  <td className="px-5 py-3 text-right font-semibold text-slate-700">{u.total_points}</td>
                </tr>
              ))}
              {data.users.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    No users found for this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {data && data.total > data.page_size && (
        <div className="flex items-center justify-between mt-4 text-sm text-slate-500">
          <span>
            Showing {(page - 1) * data.page_size + 1}&ndash;{Math.min(page * data.page_size, data.total)} of {data.total}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </Layout>
  );
}
