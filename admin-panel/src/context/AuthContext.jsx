import { createContext, useContext, useEffect, useState } from 'react';
import { fetchMe, getToken, clearToken, login as apiLogin } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then((data) => setUser(data))
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = async (username, password) => {
    await apiLogin(username, password);
    const me = await fetchMe();
    setUser(me);
  };

  const logout = () => {
    clearToken();
    setUser(null);
    window.location.href = '/admin/login';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
