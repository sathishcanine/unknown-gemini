import Sidebar from './Sidebar';

export default function Layout({ title, subtitle, children }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <main className="ml-64 p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
        </div>
        {children}
      </main>
    </div>
  );
}
