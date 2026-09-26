import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
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
  ExternalLink,
} from 'lucide-react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import {
  fetchUserDetail,
  fetchUserTimeline,
  fetchUserPlanPrices,
  saveUserPlanPrices,
  fetchUserEntitlement,
  grantUserPremium,
  revokeUserPremium,
  fetchAdminPlans,
} from '../lib/api';
import { formatISTDate, formatISTDateTime } from '../lib/formatTime';

const EVENT_LABELS = {
  app_open: 'Opened App',
  quiz_started: 'Started Test',
  quiz_completed: 'Completed Test',
  explanation_viewed: 'Viewed Explanation',
  sign_in: 'Signed In',
  sign_out: 'Signed Out',
};

function eventLabel(evt) {
  return EVENT_LABELS[evt.event_type] || evt.event_type;
}

function eventDetail(evt) {
  const meta = evt.meta_data || {};
  if (evt.event_type === 'quiz_started') return meta.topic ? `Topic: ${meta.topic}` : null;
  if (evt.event_type === 'quiz_completed')
    return meta.topic ? `${meta.topic} \u2014 ${Math.round(meta.accuracy || 0)}% accuracy` : null;
  if (evt.event_type === 'sign_in' && meta.method) {
    return meta.method === 'guest' ? 'Guest login' : `Method: ${meta.method}`;
  }
  return null;
}

function isGuestEmail(email) {
  return typeof email === 'string' && email.endsWith('@guest.local');
}

function errMsg(e, fallback) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  return fallback;
}

export default function UserDetail() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [planRows, setPlanRows] = useState([]);
  const [planDraft, setPlanDraft] = useState({});
  const [planSaving, setPlanSaving] = useState(false);
  const [planMsg, setPlanMsg] = useState(null);
  const [entitlement, setEntitlement] = useState(null);
  const [premBusy, setPremBusy] = useState(false);
  const [premMsg, setPremMsg] = useState(null);
  const [grantMode, setGrantMode] = useState('plan'); // plan | custom
  const [grantPlan, setGrantPlan] = useState('');
  const [grantDays, setGrantDays] = useState(30);
  const [activePlans, setActivePlans] = useState([]);

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

  useEffect(() => {
    fetchUserPlanPrices(userId)
      .then((data) => {
        const plans = data.plans || [];
        setPlanRows(plans);
        const draft = {};
        plans.forEach((p) => {
          draft[p.code] = p.has_override ? String(p.override_price_inr) : '';
        });
        setPlanDraft(draft);
      })
      .catch(() => {
        setPlanRows([]);
        setPlanDraft({});
      });
    fetchUserEntitlement(userId)
      .then(setEntitlement)
      .catch(() => setEntitlement(null));
    fetchAdminPlans(false)
      .then((data) => {
        const plans = (data.plans || []).filter((p) => p.is_active);
        setActivePlans(plans);
        if (plans.length) setGrantPlan((prev) => prev || plans[plans.length - 1].code);
      })
      .catch(() => setActivePlans([]));
  }, [userId]);

  const defaultPriceSummary = useMemo(() => {
    if (!planRows.length) return 'No active plans';
    return planRows.map((p) => `₹${p.default_price_inr}`).join(' / ');
  }, [planRows]);

  const hasAnyOverride = planRows.some((p) => p.has_override);

  async function handleGrantPremium() {
    setPremBusy(true);
    setPremMsg(null);
    try {
      const body =
        grantMode === 'custom'
          ? { days: Number(grantDays) || 30 }
          : { plan_code: grantPlan || '1y' };
      if (grantMode === 'custom' && (!Number(grantDays) || Number(grantDays) < 1)) {
        setPremMsg('Enter days >= 1');
        setPremBusy(false);
        return;
      }
      const data = await grantUserPremium(userId, body);
      setEntitlement(data);
      setPremMsg(
        grantMode === 'custom'
          ? `Granted premium for ${grantDays} days.`
          : `Granted premium (${grantPlan}).`
      );
    } catch (e) {
      setPremMsg(errMsg(e, 'Grant failed'));
    } finally {
      setPremBusy(false);
    }
  }

  async function handleRevokePremium() {
    if (!window.confirm('Revoke premium for this user immediately?')) return;
    setPremBusy(true);
    setPremMsg(null);
    try {
      const data = await revokeUserPremium(userId);
      setEntitlement(data);
      setPremMsg('Premium revoked.');
    } catch (e) {
      setPremMsg(errMsg(e, 'Revoke failed'));
    } finally {
      setPremBusy(false);
    }
  }

  async function handleSavePlanPrices() {
    setPlanSaving(true);
    setPlanMsg(null);
    try {
      for (const p of planRows) {
        const raw = (planDraft[p.code] ?? '').toString().trim();
        if (raw !== '' && (Number.isNaN(Number(raw)) || Number(raw) < 0)) {
          setPlanMsg(`Invalid price for ${p.name}`);
          setPlanSaving(false);
          return;
        }
      }
      const overrides = planRows.map((p) => {
        const raw = (planDraft[p.code] ?? '').toString().trim();
        return {
          plan_code: p.code,
          price_inr: raw === '' ? null : Number(raw),
          note: raw === '' ? null : 'Admin override',
        };
      });
      const data = await saveUserPlanPrices(userId, overrides);
      const plans = data.plans || [];
      setPlanRows(plans);
      const draft = {};
      plans.forEach((p) => {
        draft[p.code] = p.has_override ? String(p.override_price_inr) : '';
      });
      setPlanDraft(draft);
      setPlanMsg('Saved — only this user sees these prices in the app.');
    } catch (e) {
      setPlanMsg(errMsg(e, 'Failed to save prices'));
    } finally {
      setPlanSaving(false);
    }
  }

  async function handleClearAllOverrides() {
    if (!window.confirm('Clear all custom prices for this user? They will see global defaults.')) return;
    setPlanSaving(true);
    setPlanMsg(null);
    try {
      const overrides = planRows.map((p) => ({
        plan_code: p.code,
        price_inr: null,
        note: null,
      }));
      const data = await saveUserPlanPrices(userId, overrides);
      const plans = data.plans || [];
      setPlanRows(plans);
      const draft = {};
      plans.forEach((p) => {
        draft[p.code] = '';
      });
      setPlanDraft(draft);
      setPlanMsg('All overrides cleared.');
    } catch (e) {
      setPlanMsg(errMsg(e, 'Failed to clear overrides'));
    } finally {
      setPlanSaving(false);
    }
  }

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
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-4">Profile</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-slate-600">
                <Mail size={15} className="text-slate-400" /> {profile.email}
              </div>
              {isGuestEmail(profile.email) && (
                <div className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
                  Guest
                </div>
              )}
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
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-1">Premium Access</h3>
            <p className="text-sm text-slate-700 mb-3">
              Status:{' '}
              <span className={entitlement?.is_premium ? 'text-emerald-600 font-semibold' : 'text-slate-500'}>
                {entitlement?.is_premium ? 'Active' : 'Not premium'}
              </span>
              {entitlement?.premium_expires_at ? (
                <span className="block text-xs text-slate-400 mt-1">
                  Expires {formatISTDateTime(entitlement.premium_expires_at)}
                </span>
              ) : null}
            </p>

            <div className="flex gap-2 mb-3">
              <button
                type="button"
                onClick={() => setGrantMode('plan')}
                className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${
                  grantMode === 'plan' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                By package
              </button>
              <button
                type="button"
                onClick={() => setGrantMode('custom')}
                className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${
                  grantMode === 'custom' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                Custom days
              </button>
            </div>

            {grantMode === 'plan' ? (
              <select
                value={grantPlan}
                onChange={(e) => setGrantPlan(e.target.value)}
                className="w-full mb-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                {activePlans.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name} ({p.duration_days}d)
                  </option>
                ))}
                {activePlans.length === 0 && <option value="1y">1 Year</option>}
              </select>
            ) : (
              <div className="flex items-center gap-2 mb-3">
                <input
                  type="number"
                  min={1}
                  value={grantDays}
                  onChange={(e) => setGrantDays(e.target.value)}
                  className="w-24 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
                <span className="text-sm text-slate-500">days</span>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={premBusy}
                onClick={handleGrantPremium}
                className="rounded-lg bg-amber-500 text-white text-xs font-semibold px-3 py-2 disabled:opacity-50"
              >
                Grant premium
              </button>
              <button
                type="button"
                disabled={premBusy || !entitlement?.is_premium}
                onClick={handleRevokePremium}
                className="rounded-lg border border-rose-200 text-rose-600 text-xs font-semibold px-3 py-2 disabled:opacity-50"
              >
                Revoke
              </button>
            </div>
            {premMsg && <p className="mt-2 text-xs text-slate-600">{premMsg}</p>}
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <div className="flex items-start justify-between gap-2 mb-1">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide">
                Prices for this user
              </h3>
              <Link
                to="/pricing"
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-700"
              >
                Global packages <ExternalLink size={11} />
              </Link>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Defaults: {defaultPriceSummary}. Leave blank to use the global default. Changes apply only
              to this student.
            </p>
            <div className="space-y-3">
              {planRows.map((p) => (
                <div key={p.code} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                      {p.name}
                      {p.has_override && (
                        <span className="rounded-full bg-amber-50 text-amber-700 text-[10px] font-bold px-1.5 py-0.5">
                          Custom
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400">
                      Default ₹{p.default_price_inr}
                      {p.updated_at ? ` · set ${formatISTDateTime(p.updated_at)}` : ''}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-sm text-slate-500">₹</span>
                    <input
                      type="number"
                      min="0"
                      placeholder={String(p.default_price_inr)}
                      value={planDraft[p.code] ?? ''}
                      onChange={(e) =>
                        setPlanDraft((prev) => ({ ...prev, [p.code]: e.target.value }))
                      }
                      className="w-20 rounded-lg border border-slate-200 px-2 py-1.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
                    />
                  </div>
                </div>
              ))}
              {planRows.length === 0 && (
                <p className="text-xs text-slate-400">
                  No active plans. Create packages under{' '}
                  <Link to="/pricing" className="text-indigo-600 font-semibold">
                    Pricing
                  </Link>
                  .
                </p>
              )}
            </div>
            <button
              type="button"
              disabled={planSaving || planRows.length === 0}
              onClick={handleSavePlanPrices}
              className="mt-4 w-full rounded-xl bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white text-sm font-semibold py-2.5"
            >
              {planSaving ? 'Saving…' : 'Save prices for this user'}
            </button>
            {hasAnyOverride && (
              <button
                type="button"
                disabled={planSaving}
                onClick={handleClearAllOverrides}
                className="mt-2 w-full rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold py-2 disabled:opacity-50"
              >
                Clear all overrides
              </button>
            )}
            {planMsg && <p className="mt-2 text-xs text-slate-600">{planMsg}</p>}
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
