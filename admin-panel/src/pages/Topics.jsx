import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import FilterBar from '../components/FilterBar';
import Loading from '../components/Loading';
import { useFilter } from '../context/FilterContext';
import { fetchTopicAnalytics } from '../lib/api';

const DIFFICULTY_STYLES = {
  Easy: 'bg-emerald-50 text-emerald-600',
  Medium: 'bg-amber-50 text-amber-600',
  Hard: 'bg-rose-50 text-rose-600',
};

export default function Topics() {
  const { range } = useFilter();
  const navigate = useNavigate();
  const [topics, setTopics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTopicAnalytics({ start: range.start, end: range.end })
      .then(setTopics)
      .finally(() => setLoading(false));
  }, [range.start, range.end]);

  const withActivity = topics?.filter((t) => t.attempts > 0) || [];
  const withoutActivity = topics?.filter((t) => t.attempts === 0) || [];

  return (
    <Layout title="Topic Analytics" subtitle="Every topic and subtopic, ranked by attempts in the selected period.">
      <FilterBar />

      {loading || !topics ? (
        <Loading />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase tracking-wide">
                <th className="text-left font-semibold px-5 py-3">Topic</th>
                <th className="text-left font-semibold px-5 py-3">Subject</th>
                <th className="text-left font-semibold px-5 py-3">Difficulty</th>
                <th className="text-right font-semibold px-5 py-3">Attempts</th>
                <th className="text-right font-semibold px-5 py-3">Accuracy</th>
                <th className="text-right font-semibold px-5 py-3">Avg Time</th>
                <th className="text-right font-semibold px-5 py-3">Completion</th>
                <th className="text-right font-semibold px-5 py-3">Drop Rate</th>
              </tr>
            </thead>
            <tbody>
              {[...withActivity, ...withoutActivity].map((t) => (
                <tr
                  key={t.id}
                  onClick={() => navigate(`/questions?topic_id=${t.id}&topic_name=${encodeURIComponent(t.name)}`)}
                  className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition"
                >
                  <td className="px-5 py-3 font-semibold text-slate-800">{t.name}</td>
                  <td className="px-5 py-3 text-slate-500">{t.subject_name}</td>
                  <td className="px-5 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        DIFFICULTY_STYLES[t.difficulty] || 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {t.difficulty || '\u2014'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-slate-700">{t.attempts}</td>
                  <td className="px-5 py-3 text-right font-semibold text-slate-700">
                    {t.attempts > 0 ? `${t.accuracy}%` : '\u2014'}
                  </td>
                  <td className="px-5 py-3 text-right text-slate-500">
                    {t.avg_time_seconds != null ? `${t.avg_time_seconds}s` : '\u2014'}
                  </td>
                  <td className="px-5 py-3 text-right text-slate-500">
                    {t.completion_rate != null ? `${t.completion_rate}%` : '\u2014'}
                  </td>
                  <td className="px-5 py-3 text-right text-slate-500">
                    {t.drop_rate != null ? `${t.drop_rate}%` : '\u2014'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-slate-400 mt-3">
        Avg Time / Completion / Drop Rate populate as students use the newly instrumented app version. Click any row to inspect its questions.
      </p>
    </Layout>
  );
}
