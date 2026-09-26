import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  UserPlus,
  Target,
  Clock,
  ListChecks,
  Activity,
  IndianRupee,
  Sparkles,
  UserMinus,
  Percent,
  AlertTriangle,
  ShoppingCart,
  Flame,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import Layout from '../components/Layout';
import FilterBar from '../components/FilterBar';
import StatCard from '../components/StatCard';
import Loading from '../components/Loading';
import { useFilter } from '../context/FilterContext';
import { fetchDashboardSummary } from '../lib/api';
import { pctChange } from '../lib/dateRanges';

const PLAN_LABELS = {
  '1m': '1 Month',
  '2m': '2 Months',
  '1y': '1 Year',
};

const FUNNEL_STEPS = [
  { key: 'signed_up', label: 'Signed up', filter: 'new' },
  { key: 'activated', label: 'Opened app', filter: 'active' },
  { key: 'practiced', label: 'Took a test', filter: 'high_intent' },
  { key: 'checkout_started', label: 'Opened pay', filter: 'checkout' },
  { key: 'paid', label: 'Paid', filter: 'premium' },
];

function insightLines(data) {
  const lines = [];
  const m = data.monetization || {};
  const e = data.engagement || {};
  const p = data.period || {};
  const r = data.retention || {};
  const f = data.funnel || {};

  if ((m.checkout_abandoned || 0) > 0) {
    lines.push(
      `${m.checkout_abandoned} checkout(s) started but not paid — follow up these users (WhatsApp / grant trial).`
    );
  }

  if ((m.high_intent_free || 0) > 0) {
    lines.push(
      `${m.high_intent_free} free user(s) took 3+ tests — strongest upsell targets this period.`
    );
  }

  if ((m.premium_expiring_7d || 0) > 0) {
    lines.push(
      `${m.premium_expiring_7d} premium user(s) expire within 7 days — nudge renewals now.`
    );
  }

  if ((m.conversion_rate || 0) < 5 && (e.total_users || 0) > 20) {
    lines.push(
      `Premium conversion is ${m.conversion_rate ?? 0}% — surface Premium after the first free batch.`
    );
  } else if ((m.conversion_rate || 0) >= 5) {
    lines.push(`Premium conversion looks healthy at ${m.conversion_rate}%.`);
  }

  if ((r.d1 || 0) < 25) {
    lines.push(
      `Day-1 retention is ${r.d1}% — tighten first-session experience and WhatsApp nudge.`
    );
  }

  if ((f.signed_up || 0) > 0 && (f.activated || 0) / f.signed_up < 0.5) {
    lines.push('Over half of new signups never open the app again — check onboarding / notifications.');
  }

  if ((p.tests_per_active_user || 0) < 1 && (p.active_users || 0) > 0) {
    lines.push('Active users take fewer than 1 test each — surface “Continue practice” on Home.');
  }

  if ((m.paid_revenue_inr || 0) === 0 && (e.total_users || 0) > 0) {
    lines.push('No paid revenue in this period — verify Razorpay checkout end-to-end.');
  } else if ((m.paid_revenue_inr || 0) > 0) {
    lines.push(
      `₹${m.paid_revenue_inr} revenue from ${m.paid_orders} paid order(s). Avg ₹${m.revenue_per_active || 0} per active user.`
    );
  }

  if ((e.guest_users || 0) > (e.total_users || 0) * 0.4) {
    lines.push(
      `${e.guest_users} guest accounts — push Google Sign-In to recover payments and remarket.`
    );
  }

  return lines.slice(0, 5);
}

function shortDay(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

export default function Dashboard() {
  const { range, compareEnabled } = useFilter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = { start: range.start, end: range.end };
    if (compareEnabled && range.compareStart) {
      params.compare_start = range.compareStart;
      params.compare_end = range.compareEnd;
    }
    fetchDashboardSummary(params)
      .then(setData)
      .finally(() => setLoading(false));
  }, [range.start, range.end, range.compareStart, range.compareEnd, compareEnabled]);

  const usersQs = (filter) => {
    const q = new URLSearchParams();
    if (filter) q.set('filter', filter);
    q.set('start', range.start);
    q.set('end', range.end);
    return `/users?${q.toString()}`;
  };

  const funnelMax = Math.max(1, ...(FUNNEL_STEPS.map((s) => data?.funnel?.[s.key] || 0)));

  return (
    <Layout title="Executive Dashboard" subtitle="Click any card to drill into the students behind the number.">
      <FilterBar />

      {loading || !data ? (
        <Loading />
      ) : (
        <div className="space-y-8">
          <section className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-amber-300" />
              <h2 className="text-sm font-bold uppercase tracking-wide text-amber-200">Business insights</h2>
            </div>
            <ul className="space-y-2">
              {insightLines(data).map((line) => (
                <li key={line} className="text-sm text-slate-200 leading-relaxed flex gap-2">
                  <span className="text-amber-300 mt-0.5">•</span>
                  <span>{line}</span>
                </li>
              ))}
              {insightLines(data).length === 0 && (
                <li className="text-sm text-slate-300">Not enough data yet — keep the app running for a few more days.</li>
              )}
            </ul>
          </section>

          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">Users (Live)</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="DAU" value={data.engagement.dau} icon={Users} accent="indigo" to={usersQs('dau')} hint="Active in last 24 hours" />
              <StatCard label="WAU" value={data.engagement.wau} icon={Users} accent="indigo" to={usersQs('wau')} hint="Active in last 7 days" />
              <StatCard label="MAU" value={data.engagement.mau} icon={Users} accent="indigo" to={usersQs('mau')} hint="Active in last 30 days" />
              <StatCard label="Total Users" value={data.engagement.total_users} icon={Users} accent="slate" to={usersQs()} hint="All registered accounts" />
            </div>
          </section>

          {(data.daily || []).length > 0 && (
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <h3 className="text-sm font-bold text-slate-700 mb-1">Users &amp; practice trend</h3>
                <p className="text-xs text-slate-400 mb-4">Daily new / active users and tests in selected period</p>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.daily}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" tickFormatter={shortDay} tick={{ fontSize: 11 }} stroke="#94a3b8" />
                      <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" allowDecimals={false} />
                      <Tooltip labelFormatter={(v) => shortDay(v)} />
                      <Area type="monotone" dataKey="active_users" name="Active" stroke="#4f46e5" fill="#c7d2fe" strokeWidth={2} />
                      <Area type="monotone" dataKey="new_users" name="New" stroke="#059669" fill="#a7f3d0" strokeWidth={2} />
                      <Area type="monotone" dataKey="tests" name="Tests" stroke="#d97706" fill="#fde68a" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <h3 className="text-sm font-bold text-slate-700 mb-1">Revenue trend</h3>
                <p className="text-xs text-slate-400 mb-4">Paid Razorpay revenue by day (₹)</p>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.daily}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" tickFormatter={shortDay} tick={{ fontSize: 11 }} stroke="#94a3b8" />
                      <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" allowDecimals={false} />
                      <Tooltip labelFormatter={(v) => shortDay(v)} formatter={(v) => [`₹${v}`, 'Revenue']} />
                      <Bar dataKey="revenue" name="Revenue" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </section>
          )}

          <section>
            <div className="flex items-end justify-between mb-3 gap-3">
              <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide">
                Signup → Pay funnel (new users in {range.label})
              </h2>
              <Link to={usersQs('inactive')} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
                View drop-offs →
              </Link>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="space-y-3">
                {FUNNEL_STEPS.map((step, idx) => {
                  const value = data.funnel?.[step.key] || 0;
                  const prev = idx === 0 ? value : data.funnel?.[FUNNEL_STEPS[idx - 1].key] || 0;
                  const stepRate = prev > 0 ? Math.round((value / prev) * 100) : 0;
                  const width = Math.max(6, Math.round((value / funnelMax) * 100));
                  return (
                    <Link key={step.key} to={usersQs(step.filter)} className="block group">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-medium text-slate-700 group-hover:text-indigo-700">
                          {idx + 1}. {step.label}
                        </span>
                        <span className="text-slate-500">
                          <span className="font-bold text-slate-900">{value}</span>
                          {idx > 0 && <span className="ml-2 text-xs">{stepRate}% of prior</span>}
                        </span>
                      </div>
                      <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-500 group-hover:bg-indigo-600 transition-all"
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">
              Selected Period &mdash; {range.label}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                label="New Users"
                value={data.period.new_users}
                delta={compareEnabled ? pctChange(data.period.new_users, data.comparison?.new_users) : null}
                icon={UserPlus}
                accent="emerald"
                to={usersQs('new')}
                hint="Joined in this date range"
              />
              <StatCard
                label="Active Users"
                value={data.period.active_users}
                delta={compareEnabled ? pctChange(data.period.active_users, data.comparison?.active_users) : null}
                icon={Activity}
                accent="indigo"
                to={usersQs('active')}
                hint="Opened app in this period"
              />
              <StatCard
                label="Tests Taken"
                value={data.period.total_tests}
                delta={compareEnabled ? pctChange(data.period.total_tests, data.comparison?.total_tests) : null}
                icon={ListChecks}
                accent="amber"
                to="/topics"
                hint="Open topic analytics"
              />
              <StatCard
                label="Questions Solved"
                value={data.period.questions_solved}
                delta={compareEnabled ? pctChange(data.period.questions_solved, data.comparison?.questions_solved) : null}
                icon={Target}
                accent="indigo"
                to="/questions"
                hint="Open question analytics"
              />
              <StatCard
                label="Overall Accuracy"
                value={data.period.accuracy}
                suffix="%"
                delta={compareEnabled ? pctChange(data.period.accuracy, data.comparison?.accuracy) : null}
                icon={Target}
                accent="emerald"
                to="/questions"
                hint="See hardest questions"
              />
              <StatCard
                label="Avg Session"
                value={Math.round((data.period.avg_session_seconds / 60) * 10) / 10}
                suffix=" min"
                delta={
                  compareEnabled
                    ? pctChange(data.period.avg_session_seconds, data.comparison?.avg_session_seconds)
                    : null
                }
                icon={Clock}
                accent="slate"
                to={usersQs('active')}
                hint="Active users this period"
              />
              <StatCard
                label="Tests / Active User"
                value={data.period.tests_per_active_user ?? 0}
                icon={ListChecks}
                accent="amber"
                to={usersQs('high_intent')}
                hint="Depth of practice"
              />
              <StatCard
                label="Guest Users"
                value={data.engagement.guest_users ?? 0}
                icon={UserMinus}
                accent="slate"
                to={usersQs('guest')}
                hint="Not signed in with Google"
              />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">Monetization</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                label="Premium Users"
                value={data.monetization?.premium_users ?? 0}
                icon={Sparkles}
                accent="amber"
                to={usersQs('premium')}
                hint="Currently active premium"
              />
              <StatCard
                label="Free Users"
                value={data.monetization?.free_users ?? data.engagement.free_users ?? 0}
                icon={Users}
                accent="slate"
                to={usersQs('free')}
              />
              <StatCard
                label="Conversion"
                value={data.monetization?.conversion_rate ?? 0}
                suffix="%"
                icon={Percent}
                accent="emerald"
                to={usersQs('premium')}
                hint="Premium ÷ total users"
              />
              <StatCard
                label="Paid Orders"
                value={data.monetization?.paid_orders ?? 0}
                icon={IndianRupee}
                accent="emerald"
                to="/pricing"
                hint="Successful Razorpay payments"
              />
              <StatCard
                label="Revenue (period)"
                value={data.monetization?.paid_revenue_inr ?? 0}
                prefix="₹"
                icon={IndianRupee}
                accent="indigo"
                to="/pricing"
              />
              <StatCard
                label="₹ / Active User"
                value={data.monetization?.revenue_per_active ?? 0}
                prefix="₹"
                icon={IndianRupee}
                accent="amber"
                hint="Period revenue ÷ active users"
                to={usersQs('active')}
              />
              <StatCard
                label="Checkout Abandoned"
                value={data.monetization?.checkout_abandoned ?? 0}
                icon={ShoppingCart}
                accent="rose"
                to={usersQs('checkout')}
                hint="Opened pay but did not finish"
              />
              <StatCard
                label="Checkout → Pay"
                value={data.monetization?.checkout_conversion ?? 0}
                suffix="%"
                icon={Percent}
                accent="indigo"
                to={usersQs('checkout')}
                hint="Paid ÷ checkouts started"
              />
              <StatCard
                label="Expiring in 7d"
                value={data.monetization?.premium_expiring_7d ?? 0}
                icon={AlertTriangle}
                accent="amber"
                to={usersQs('expiring')}
                hint="Renewal nudge list"
              />
              <StatCard
                label="High-intent Free"
                value={data.monetization?.high_intent_free ?? 0}
                icon={Flame}
                accent="rose"
                to={usersQs('high_intent')}
                hint="Free users with 3+ tests"
              />
              <StatCard label="Pricing" value="Edit" icon={IndianRupee} accent="indigo" to="/pricing" hint="Plans & defaults" />
              <StatCard
                label="Ad Revenue"
                value={data.not_tracked?.ad_revenue}
                icon={IndianRupee}
                accent="slate"
                hint="Not tracked yet"
              />
            </div>

            {(data.monetization?.plan_sales || []).length > 0 && (
              <div className="mt-4 bg-white border border-slate-200 rounded-2xl overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-100 text-xs font-bold text-slate-400 uppercase tracking-wide">
                  Plan mix (this period)
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-50">
                      <th className="text-left font-semibold px-5 py-2">Plan</th>
                      <th className="text-right font-semibold px-5 py-2">Orders</th>
                      <th className="text-right font-semibold px-5 py-2">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.monetization.plan_sales.map((row) => (
                      <tr key={row.plan_code} className="border-b border-slate-50">
                        <td className="px-5 py-2.5 font-medium text-slate-800">
                          {PLAN_LABELS[row.plan_code] || row.plan_code}
                        </td>
                        <td className="px-5 py-2.5 text-right text-slate-600">{row.orders}</td>
                        <td className="px-5 py-2.5 text-right font-semibold text-slate-800">₹{row.revenue}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">Retention</h2>
            <div className="grid grid-cols-3 gap-4">
              <StatCard
                label="Day 1 Retention"
                value={data.retention.d1}
                suffix="%"
                accent="indigo"
                to={usersQs('inactive')}
                hint="% returned next day — click for drop-offs"
              />
              <StatCard
                label="Day 7 Retention"
                value={data.retention.d7}
                suffix="%"
                accent="indigo"
                to={usersQs('wau')}
                hint="% returned on day 7"
              />
              <StatCard
                label="Day 30 Retention"
                value={data.retention.d30}
                suffix="%"
                accent="indigo"
                to={usersQs('mau')}
                hint="% returned on day 30"
              />
            </div>
          </section>
        </div>
      )}
    </Layout>
  );
}
