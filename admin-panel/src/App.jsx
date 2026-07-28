import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { FilterProvider } from './context/FilterContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import UserDetail from './pages/UserDetail';
import Topics from './pages/Topics';
import Questions from './pages/Questions';
import Leaderboard from './pages/Leaderboard';
import ComingSoon from './components/ComingSoon';
import Layout from './components/Layout';
import Loading from './components/Loading';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loading />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Loading />
      </div>
    );
  }
  if (user) return <Navigate to="/" replace />;
  return children;
}

function SearchPage() {
  return (
    <Layout title="Search Analytics" subtitle="What students are looking for">
      <ComingSoon
        title="Search Analytics coming soon"
        description="This will light up once the app has an in-app search feature. We'll track queries so you know exactly what aspirants want."
      />
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter basename="/admin">
      <AuthProvider>
        <FilterProvider>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicOnlyRoute>
                  <Login />
                </PublicOnlyRoute>
              }
            />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/users"
              element={
                <ProtectedRoute>
                  <Users />
                </ProtectedRoute>
              }
            />
            <Route
              path="/users/:userId"
              element={
                <ProtectedRoute>
                  <UserDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/topics"
              element={
                <ProtectedRoute>
                  <Topics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/questions"
              element={
                <ProtectedRoute>
                  <Questions />
                </ProtectedRoute>
              }
            />
            <Route
              path="/search"
              element={
                <ProtectedRoute>
                  <SearchPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/leaderboard"
              element={
                <ProtectedRoute>
                  <Leaderboard />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </FilterProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
