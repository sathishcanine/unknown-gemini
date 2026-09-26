import { useEffect, useMemo, useState } from 'react';
import {
  Plus,
  Pencil,
  Trash2,
  Power,
  ArrowUp,
  ArrowDown,
  IndianRupee,
  Users as UsersIcon,
  Info,
} from 'lucide-react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import {
  fetchAdminPlans,
  createAdminPlan,
  updateAdminPlan,
  deleteAdminPlan,
  reorderAdminPlans,
} from '../lib/api';

const EMPTY_FORM = {
  code: '',
  name: '',
  name_ta: '',
  duration_days: 60,
  price_inr: 99,
  is_active: true,
};

function errMsg(e, fallback) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join('; ');
  return fallback;
}

export default function Pricing() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const activeCount = useMemo(() => plans.filter((p) => p.is_active).length, [plans]);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const data = await fetchAdminPlans(true);
      setPlans(data.plans || []);
    } catch (e) {
      setErr(errMsg(e, 'Failed to load plans'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
    setMsg(null);
    setErr(null);
  }

  function openEdit(plan) {
    setEditing(plan);
    setForm({
      code: plan.code,
      name: plan.name || '',
      name_ta: plan.name_ta || '',
      duration_days: plan.duration_days,
      price_inr: plan.price_inr,
      is_active: !!plan.is_active,
    });
    setShowForm(true);
    setMsg(null);
    setErr(null);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setErr(null);
    setMsg(null);
    try {
      if (editing) {
        await updateAdminPlan(editing.id, {
          name: form.name.trim(),
          name_ta: form.name_ta.trim() || null,
          duration_days: Number(form.duration_days),
          price_inr: Number(form.price_inr),
          is_active: !!form.is_active,
        });
        setMsg(`Updated “${form.name.trim()}”. App users see this immediately.`);
      } else {
        await createAdminPlan({
          code: form.code.trim().toLowerCase(),
          name: form.name.trim(),
          name_ta: form.name_ta.trim() || null,
          duration_days: Number(form.duration_days),
          price_inr: Number(form.price_inr),
          is_active: !!form.is_active,
        });
        setMsg(`Created plan “${form.name.trim()}”.`);
      }
      setShowForm(false);
      setEditing(null);
      await load();
    } catch (ex) {
      setErr(errMsg(ex, 'Save failed'));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(plan) {
    setBusyId(plan.id);
    setErr(null);
    setMsg(null);
    try {
      await updateAdminPlan(plan.id, { is_active: !plan.is_active });
      setMsg(
        plan.is_active
          ? `Deactivated “${plan.name}” — hidden from the app.`
          : `Activated “${plan.name}” — visible in the app.`
      );
      await load();
    } catch (ex) {
      setErr(errMsg(ex, 'Could not update status'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleSoftDelete(plan) {
    const ok = window.confirm(
      `Deactivate “${plan.name}” (${plan.code})?\n\nIt will disappear from the app. Payment history is kept. You can reactivate later.`
    );
    if (!ok) return;
    setBusyId(plan.id);
    setErr(null);
    try {
      await deleteAdminPlan(plan.id, { force: false });
      setMsg(`Deactivated “${plan.name}”.`);
      await load();
    } catch (ex) {
      setErr(errMsg(ex, 'Deactivate failed'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleHardDelete(plan) {
    if (plan.order_count > 0) {
      setErr('This plan has payment history — deactivate instead of permanent delete.');
      return;
    }
    const ok = window.confirm(
      `Permanently delete “${plan.name}” (${plan.code})?\n\nThis cannot be undone. Only allowed when there are zero payment orders.`
    );
    if (!ok) return;
    setBusyId(plan.id);
    setErr(null);
    try {
      await deleteAdminPlan(plan.id, { force: true });
      setMsg(`Permanently deleted “${plan.name}”.`);
      await load();
    } catch (ex) {
      setErr(errMsg(ex, 'Delete failed'));
    } finally {
      setBusyId(null);
    }
  }

  async function movePlan(plan, direction) {
    const idx = plans.findIndex((p) => p.id === plan.id);
    if (idx < 0) return;
    const swapWith = direction === 'up' ? idx - 1 : idx + 1;
    if (swapWith < 0 || swapWith >= plans.length) return;
    const next = [...plans];
    [next[idx], next[swapWith]] = [next[swapWith], next[idx]];
    setBusyId(plan.id);
    setErr(null);
    try {
      const data = await reorderAdminPlans(next.map((p) => p.id));
      setPlans(data.plans || next);
      setMsg('Display order updated.');
    } catch (ex) {
      setErr(errMsg(ex, 'Reorder failed'));
      await load();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Layout
      title="Pricing Packages"
      subtitle="Default plans shown to all users. Per-user discounts live on each student profile."
    >
      <div className="mb-5 rounded-2xl border border-indigo-100 bg-indigo-50/60 px-4 py-3 flex gap-3 text-sm text-slate-700">
        <Info size={18} className="text-indigo-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-slate-800">How pricing works</p>
          <ul className="mt-1 text-xs text-slate-600 space-y-0.5 list-disc list-inside">
            <li>
              <strong>This page</strong> — global packages (add / edit / activate / deactivate / reorder).
            </li>
            <li>
              <strong>Users → student profile</strong> — override price for one person, or grant / revoke
              Premium without payment.
            </li>
            <li>Inactive plans stay in history but are hidden from the app checkout.</li>
            <li>You must keep at least one active plan.</li>
          </ul>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="text-sm text-slate-500">
          {activeCount} active · {plans.length} total
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2.5"
        >
          <Plus size={16} /> Add package
        </button>
      </div>

      {(msg || err) && (
        <div
          className={`mb-4 rounded-xl px-4 py-2.5 text-sm ${
            err ? 'bg-rose-50 text-rose-700 border border-rose-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
          }`}
        >
          {err || msg}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleSave}
          className="mb-6 bg-white border border-slate-200 rounded-2xl p-5 space-y-4"
        >
          <h3 className="text-sm font-bold text-slate-800">
            {editing ? `Edit package · ${editing.code}` : 'New package'}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Code" hint="Immutable after create · e.g. 2m, 6m, 1y">
              <input
                required
                disabled={!!editing}
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                placeholder="6m"
                className="field-input disabled:bg-slate-50 disabled:text-slate-400"
              />
            </Field>
            <Field label="Display name (English)">
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="6 Months"
                className="field-input"
              />
            </Field>
            <Field label="Display name (Tamil)" hint="Optional">
              <input
                value={form.name_ta}
                onChange={(e) => setForm((f) => ({ ...f, name_ta: e.target.value }))}
                placeholder="6 மாதங்கள்"
                className="field-input"
              />
            </Field>
            <Field label="Duration (days)">
              <input
                required
                type="number"
                min={1}
                value={form.duration_days}
                onChange={(e) => setForm((f) => ({ ...f, duration_days: e.target.value }))}
                className="field-input"
              />
            </Field>
            <Field label="Default price (₹)">
              <input
                required
                type="number"
                min={0}
                value={form.price_inr}
                onChange={(e) => setForm((f) => ({ ...f, price_inr: e.target.value }))}
                className="field-input"
              />
            </Field>
            <Field label="Status">
              <label className="flex items-center gap-2 text-sm text-slate-700 h-[42px]">
                <input
                  type="checkbox"
                  checked={!!form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-slate-300"
                />
                Active (visible in app)
              </label>
            </Field>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2.5"
            >
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Create package'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setEditing(null);
              }}
              className="rounded-xl border border-slate-200 text-slate-600 text-sm font-semibold px-4 py-2.5"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        {loading ? (
          <Loading />
        ) : plans.length === 0 ? (
          <p className="text-sm text-slate-400 py-12 text-center">No packages yet. Add your first one.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase tracking-wide">
                <th className="text-left font-semibold px-4 py-3 w-16">Order</th>
                <th className="text-left font-semibold px-4 py-3">Package</th>
                <th className="text-right font-semibold px-4 py-3">Price</th>
                <th className="text-right font-semibold px-4 py-3">Days</th>
                <th className="text-left font-semibold px-4 py-3">Status</th>
                <th className="text-right font-semibold px-4 py-3">Usage</th>
                <th className="text-right font-semibold px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p, i) => (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50/80">
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <button
                        type="button"
                        disabled={busyId === p.id || i === 0}
                        onClick={() => movePlan(p, 'up')}
                        className="p-1 rounded text-slate-400 hover:text-slate-700 disabled:opacity-30"
                        title="Move up"
                      >
                        <ArrowUp size={14} />
                      </button>
                      <button
                        type="button"
                        disabled={busyId === p.id || i === plans.length - 1}
                        onClick={() => movePlan(p, 'down')}
                        className="p-1 rounded text-slate-400 hover:text-slate-700 disabled:opacity-30"
                        title="Move down"
                      >
                        <ArrowDown size={14} />
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-800">{p.name}</div>
                    <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                      <code className="bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">{p.code}</code>
                      {p.name_ta ? <span>{p.name_ta}</span> : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-slate-800">
                    <span className="inline-flex items-center gap-0.5 justify-end">
                      <IndianRupee size={13} className="text-slate-400" />
                      {p.price_inr}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-600">{p.duration_days}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        p.is_active
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {p.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-slate-500">
                    <div className="inline-flex flex-col items-end gap-0.5">
                      <span className="inline-flex items-center gap-1">
                        <UsersIcon size={11} /> {p.override_count} overrides
                      </span>
                      <span>
                        {p.paid_order_count} paid / {p.order_count} orders
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <IconBtn title="Edit" onClick={() => openEdit(p)} disabled={busyId === p.id}>
                        <Pencil size={14} />
                      </IconBtn>
                      <IconBtn
                        title={p.is_active ? 'Deactivate' : 'Activate'}
                        onClick={() => toggleActive(p)}
                        disabled={busyId === p.id}
                      >
                        <Power size={14} />
                      </IconBtn>
                      <IconBtn
                        title="Deactivate (soft delete)"
                        onClick={() => handleSoftDelete(p)}
                        disabled={busyId === p.id || !p.is_active}
                        danger
                      >
                        <Trash2 size={14} />
                      </IconBtn>
                      {p.order_count === 0 && (
                        <button
                          type="button"
                          disabled={busyId === p.id}
                          onClick={() => handleHardDelete(p)}
                          className="text-[10px] font-semibold text-rose-500 hover:text-rose-700 px-1.5 disabled:opacity-40"
                          title="Permanent delete (no payment history)"
                        >
                          Purge
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style>{`
        .field-input {
          width: 100%;
          border: 1px solid #e2e8f0;
          border-radius: 0.75rem;
          padding: 0.55rem 0.75rem;
          font-size: 0.875rem;
          color: #1e293b;
          outline: none;
        }
        .field-input:focus {
          box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.35);
          border-color: #a5b4fc;
        }
      `}</style>
    </Layout>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
        {label}
      </span>
      {children}
      {hint ? <span className="block text-[11px] text-slate-400 mt-1">{hint}</span> : null}
    </label>
  );
}

function IconBtn({ children, onClick, disabled, title, danger }) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`p-2 rounded-lg border border-slate-200 hover:bg-white disabled:opacity-40 ${
        danger ? 'text-rose-500 hover:border-rose-200' : 'text-slate-600'
      }`}
    >
      {children}
    </button>
  );
}
