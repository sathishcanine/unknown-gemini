import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';
import Layout from '../components/Layout';
import FilterBar from '../components/FilterBar';
import Loading from '../components/Loading';
import { useFilter } from '../context/FilterContext';
import { fetchQuestionAnalytics } from '../lib/api';

const SORT_OPTIONS = [
  { id: 'attempts', label: 'Most Attempted' },
  { id: 'correct_pct', label: 'Most Confusing (Lowest Accuracy)' },
  { id: 'wrong_count', label: 'Most Incorrect' },
  { id: 'skipped_count', label: 'Most Skipped' },
  { id: 'avg_time_seconds', label: 'Most Time Taken' },
];

export default function Questions() {
  const { range } = useFilter();
  const [params] = useSearchParams();
  const topicId = params.get('topic_id');
  const topicName = params.get('topic_name');

  const [sortBy, setSortBy] = useState('attempts');
  const [questions, setQuestions] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchQuestionAnalytics({
      start: range.start,
      end: range.end,
      topic_id: topicId || undefined,
      sort_by: sortBy,
      page_size: 50,
    })
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, [range.start, range.end, topicId, sortBy]);

  return (
    <Layout
      title="Question Analytics"
      subtitle={topicName ? `Every question in "${topicName}"` : 'Every question, ranked by engagement in the selected period.'}
    >
      <FilterBar />

      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
        {SORT_OPTIONS.map((o) => (
          <button
            key={o.id}
            onClick={() => setSortBy(o.id)}
            className={`whitespace-nowrap px-3.5 py-2 rounded-xl text-sm font-medium border transition ${
              sortBy === o.id
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {loading || !questions ? (
        <Loading />
      ) : (
        <div className="space-y-3">
          {questions.map((q) => (
            <div key={q.id} className="bg-white border border-slate-200 rounded-2xl p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-semibold text-slate-400">#{q.id}</span>
                    <span className="text-xs font-semibold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full">
                      {q.topic_name}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">{q.difficulty}</span>
                  </div>
                  <p className="text-sm text-slate-700">{q.question_en}</p>
                </div>
                <div className="flex gap-4 text-center flex-shrink-0">
                  <MiniStat label="Attempts" value={q.attempts} />
                  <MiniStat label="Correct" value={`${q.correct_pct}%`} color="text-emerald-600" />
                  <MiniStat label="Wrong" value={`${q.wrong_pct}%`} color="text-rose-600" />
                  <MiniStat label="Skipped" value={`${q.skipped_pct}%`} color="text-slate-400" />
                  <MiniStat label="Avg Time" value={q.avg_time_seconds != null ? `${q.avg_time_seconds}s` : '\u2014'} />
                </div>
              </div>
              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-50 text-xs text-slate-400">
                <FeatureNote icon={AlertTriangle} label="Reported" />
                <FeatureNote icon={Bookmark} label="Bookmarked" />
                <FeatureNote icon={ThumbsUp} label="Liked" />
                <FeatureNote icon={ThumbsDown} label="Disliked" />
              </div>
            </div>
          ))}
          {questions.length === 0 && (
            <div className="text-center py-16 text-slate-400 bg-white border border-slate-200 rounded-2xl">
              No question activity in this period yet.
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}

function MiniStat({ label, value, color = 'text-slate-700' }) {
  return (
    <div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
      <div className="text-[10px] text-slate-400 uppercase">{label}</div>
    </div>
  );
}

function FeatureNote({ icon: Icon, label }) {
  return (
    <span className="flex items-center gap-1">
      <Icon size={12} /> {label}: coming soon
    </span>
  );
}
