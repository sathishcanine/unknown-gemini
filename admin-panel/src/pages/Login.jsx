import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, Lock, User, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500 flex items-center justify-center mb-4">
            <GraduationCap size={28} className="text-white" />
          </div>
          <h1 className="text-white text-xl font-bold">ACE TNPSC Admin</h1>
          <p className="text-slate-400 text-sm mt-1">Sign in to access the analytics dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-900 border border-white/5 rounded-2xl p-6 space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-400 mb-1.5 block">Username</label>
            <div className="relative">
              <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-800 border border-white/5 rounded-xl pl-10 pr-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Enter admin username"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-400 mb-1.5 block">Password</label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-800 border border-white/5 rounded-xl pl-10 pr-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Enter password"
              />
            </div>
          </div>

          {error && <p className="text-rose-400 text-xs font-medium">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl py-2.5 flex items-center justify-center gap-2 transition disabled:opacity-60"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
