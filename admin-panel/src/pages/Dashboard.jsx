import { useEffect, useState } from 'react';
import { Users, UserPlus, Target, Clock, ListChecks, Activity, IndianRupee, ShieldAlert } from 'lucide-react';
import Layout from '../components/Layout';
import FilterBar from '../components/FilterBar';
import StatCard from '../components/StatCard';
import Loading from '../components/Loading';
import { useFilter } from '../context/FilterContext';
import { fetchDashboardSummary } from '../lib/api';
import { pctChange } from '../lib/dateRanges';

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

  return (
    <Layout title="Executive Dashboard" subtitle="How is my app performing today?">
      <FilterBar />

      {loading || !data ? (
        <Loading />
      ) : (
        <div className="space-y-8">
          {/* Real-time engagement gauges */}
          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">Users (Live)</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="DAU" value={data.engagement.dau} icon={Users} accent="indigo" />
              <StatCard label="WAU" value={data.engagement.wau} icon={Users} accent="indigo" />
              <StatCard label="MAU" value={data.engagement.mau} icon={Users} accent="indigo" />
              <StatCard label="Total Users" value={data.engagement.total_users} icon={Users} accent="slate" />
            </div>
          </section>

          {/* Selected period metrics */}
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
              />
              <StatCard
                label="Active Users"
                value={data.period.active_users}
                delta={compareEnabled ? pctChange(data.period.active_users, data.comparison?.active_users) : null}
                icon={Activity}
                accent="indigo"
              />
              <StatCard
                label="Tests Taken"
                value={data.period.total_tests}
                delta={compareEnabled ? pctChange(data.period.total_tests, data.comparison?.total_tests) : null}
                icon={ListChecks}
                accent="amber"
              />
              <StatCard
                label="Questions Solved"
                value={data.period.questions_solved}
                delta={compareEnabled ? pctChange(data.period.questions_solved, data.comparison?.questions_solved) : null}
                icon={Target}
                accent="indigo"
              />
              <StatCard
                label="Overall Accuracy"
                value={data.period.accuracy}
                suffix="%"
                delta={compareEnabled ? pctChange(data.period.accuracy, data.comparison?.accuracy) : null}
                icon={Target}
                accent="emerald"
              />
              <StatCard
                label="Avg Session"
                value={Math.round(data.period.avg_session_seconds / 60 * 10) / 10}
                suffix=" min"
                delta={
                  compareEnabled
                    ? pctChange(data.period.avg_session_seconds, data.comparison?.avg_session_seconds)
                    : null
                }
                icon={Clock}
                accent="slate"
              />
            </div>
          </section>

          {/* Retention cohorts */}
          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">Retention</h2>
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Day 1 Retention" value={data.retention.d1} suffix="%" accent="indigo" />
              <StatCard label="Day 7 Retention" value={data.retention.d7} suffix="%" accent="indigo" />
              <StatCard label="Day 30 Retention" value={data.retention.d30} suffix="%" accent="indigo" />
            </div>
          </section>

          {/* Not yet tracked (future features) */}
          <section>
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-3">
              Monetization &amp; Stability
              <span className="ml-2 text-[10px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full uppercase tracking-wide">
                Requires future app update
              </span>
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Ad Revenue" value={data.not_tracked.ad_revenue} icon={IndianRupee} accent="slate" />
              <StatCard label="Subscriptions" value={data.not_tracked.subscriptions} icon={IndianRupee} accent="slate" />
              <StatCard label="Premium Users" value={data.not_tracked.premium_users} icon={Users} accent="slate" />
              <StatCard label="Crash Rate" value={data.not_tracked.crash_rate} icon={ShieldAlert} accent="slate" />
            </div>
          </section>
        </div>
      )}
    </Layout>
  );
}
