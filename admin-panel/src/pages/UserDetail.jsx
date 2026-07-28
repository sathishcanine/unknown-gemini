import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Mail,
  Smartphone,
  Globe,
  Calendar,
  Flame,
  Trophy,
  BookOpen,
  BookX,
} from 'lucide-react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import { fetchUserDetail, fetchUserTimeline } from '../lib/api';
import { formatISTDate, formatISTDateTime } from '../lib/formatTime';

const EVENT_LABELS = {
  app_open: 'Opened App',
  quiz_started: 'Started Test',
  quiz_completed: 'Completed Test',
  explanation_viewed: 'Viewed Explanation',
};

function eventLabel(evt) {
  return EVENT_LABELS[evt.event_type] || evt.event_type;
}

function eventDetail(evt) {
  const meta = evt.meta_data || {};
  if (evt.event_type === 'quiz_started') return meta.topic ? `Topic: ${meta.topic}` : null;
  if (evt.event_type === 'quiz_completed')
    return meta.topic ? `${meta.topic} \u2014 ${Math.round(meta.accuracy || 0)}% accuracy` : null;
  return null;
}

export default function UserDetail() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchUserDetail(userId)
      .then(setDetail)
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(() => {
    fetchUserTimeline(userId, { page, page_size: 30 }).then((data) => {
      setTimeline((prev) => (page === 1 ? data : { ...data, events: [...(prev?.events || []), ...data.events] }));
    });
  }, [userId, page]);

  if (loading || !detail) {
    return (
      <Layout title="Student Profile">
        <Loading />
      </Layout>
    );
  }

  const { profile, stats } = detail;

  return (
    <Layout title={profile.display_name || 'Student Profile'} subtitle={profile.email}>
      <button
        onClick={() => navigate('/users')}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-5 font-medium"
      >
        <ArrowLeft size={15} /> Back to Users
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: profile + stats */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-4">Profile</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-slate-600">
                <Mail size={15} className="text-slate-400" /> {profile.email}
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Calendar size={15} className="text-slate-400" />
                Joined {formatISTDate(profile.created_at)}
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Smartphone size={15} className="text-slate-400" />
                {profile.platform || 'Unknown'} {profile.os_version ? `\u00b7 ${profile.os_version}` : ''}
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Globe size={15} className="text-slate-400" /> {profile.country || 'Unknown'}
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Trophy size={15} className="text-slate-400" /> {profile.total_points} points
              </div>
              {profile.app_version && (
                <div className="text-xs text-slate-400">App v{profile.app_version}</div>
              )}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-4">Statistics</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <Stat label="Attempted" value={stats.attempted} />
              <Stat label="Correct" value={stats.correct} color="text-emerald-600" />
              <Stat label="Wrong" value={stats.wrong} color="text-rose-600" />
              <Stat label="Skipped" value={stats.skipped} color="text-slate-400" />
              <Stat label="Accuracy" value={`${stats.accuracy}%`} />
              <Stat
                label="Avg Time / Q"
                value={stats.avg_time_seconds > 0 ? `${stats.avg_time_seconds}s` : '\u2014'}
              />
              <Stat label="Longest Session" value={`${stats.longest_session} Qs`} />
              <Stat label="Current Streak" value={`${stats.current_streak} days`} icon={Flame} />
              <Stat label="Highest Streak" value={`${stats.highest_streak} days`} icon={Trophy} />
            </div>
            <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <BookOpen size={15} className="text-emerald-500" />
                Favorite: <span className="font-semibold">{stats.favorite_subject || '\u2014'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <BookX size={15} className="text-rose-500" />
                Weakest: <span className="font-semibold">{stats.weakest_subject || '\u2014'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right column: activity timeline */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-4">Activity Timeline</h3>
            {!timeline ? (
              <Loading />
            ) : timeline.events.length === 0 ? (
              <p className="text-sm text-slate-400 py-8 text-center">No activity recorded yet.</p>
            ) : (
              <div className="space-y-0">
                {timeline.events.map((evt, i) => (
                  <div key={i} className="flex gap-3 py-3 border-b border-slate-50 last:border-0">
                    <div className="w-2 h-2 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-700">{eventLabel(evt)}</span>
                        <span className="text-xs text-slate-400">
                          {formatISTDateTime(evt.timestamp)}
                        </span>
                      </div>
                      {eventDetail(evt) && <p className="text-xs text-slate-500 mt-0.5">{eventDetail(evt)}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {timeline && timeline.events.length < timeline.total && (
              <button
                onClick={() => setPage((p) => p + 1)}
                className="w-full mt-3 text-sm font-medium text-indigo-600 hover:text-indigo-700 py-2"
              >
                Load more
              </button>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

function Stat({ label, value, color = 'text-slate-800', icon: Icon }) {
  return (
    <div>
      <div className="text-[11px] text-slate-400 uppercase tracking-wide mb-0.5 flex items-center gap-1">
        {Icon && <Icon size={11} />}
        {label}
      </div>
      <div className={`text-base font-bold ${color}`}>{value}</div>
    </div>
  );
}
