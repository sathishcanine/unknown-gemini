import axios from 'axios';

const TOKEN_KEY = 'admin_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const api = axios.create({ baseURL: '/' });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      clearToken();
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/admin/login';
      }
    }
    return Promise.reject(err);
  }
);

export async function login(username, password) {
  const res = await api.post('/api/admin/auth/login', { username, password });
  setToken(res.data.access_token);
  return res.data;
}

export async function fetchMe() {
  const res = await api.get('/api/admin/auth/me');
  return res.data;
}

export async function fetchDashboardSummary(params) {
  const res = await api.get('/api/admin/dashboard/summary', { params });
  return res.data;
}

export async function fetchUsers(params) {
  const res = await api.get('/api/admin/users', { params });
  return res.data;
}

export async function fetchUserDetail(userId) {
  const res = await api.get(`/api/admin/users/${userId}`);
  return res.data;
}

export async function fetchUserTimeline(userId, params) {
  const res = await api.get(`/api/admin/users/${userId}/timeline`, { params });
  return res.data;
}

export async function fetchTopicAnalytics(params) {
  const res = await api.get('/api/admin/topics', { params });
  return res.data;
}

export async function fetchQuestionAnalytics(params) {
  const res = await api.get('/api/admin/questions', { params });
  return res.data;
}

export async function fetchLeaderboard(params) {
  const res = await api.get('/api/admin/leaderboard', { params });
  return res.data;
}

export default api;
