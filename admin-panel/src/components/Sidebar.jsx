import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  BookOpen,
  HelpCircle,
  Search,
  Trophy,
  LogOut,
  GraduationCap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/users', icon: Users, label: 'Users' },
  { to: '/topics', icon: BookOpen, label: 'Topic Analytics' },
  { to: '/questions', icon: HelpCircle, label: 'Question Analytics' },
  { to: '/search', icon: Search, label: 'Search Analytics' },
  { to: '/leaderboard', icon: Trophy, label: 'Leaderboard' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 h-screen bg-slate-900 text-white flex flex-col fixed left-0 top-0">
      <div className="flex items-center gap-2 px-6 py-6">
        <div className="w-9 h-9 rounded-xl bg-indigo-500 flex items-center justify-center">
          <GraduationCap size={20} />
        </div>
        <div>
          <div className="font-bold text-sm leading-tight">ACE TNPSC</div>
          <div className="text-[11px] text-slate-400">Admin Panel</div>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition ${
                isActive
                  ? 'bg-indigo-500/15 text-indigo-300'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-3 py-2 mb-1">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold">
            {user?.username?.[0]?.toUpperCase() || 'A'}
          </div>
          <div className="text-sm text-slate-300 truncate">{user?.username}</div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:bg-white/5 hover:text-red-300 transition"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
