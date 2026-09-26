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

export async function fetchUserPlanPrices(userId) {
  const res = await api.get(`/api/admin/users/${userId}/plan-prices`);
  return res.data;
}

export async function saveUserPlanPrices(userId, overrides) {
  const res = await api.put(`/api/admin/users/${userId}/plan-prices`, { overrides });
  return res.data;
}

export async function fetchUserEntitlement(userId) {
  const res = await api.get(`/api/admin/users/${userId}/entitlement`);
  return res.data;
}

export async function grantUserPremium(userId, body = { plan_code: '1y' }) {
  const res = await api.post(`/api/admin/users/${userId}/grant-premium`, body);
  return res.data;
}

export async function revokeUserPremium(userId) {
  const res = await api.post(`/api/admin/users/${userId}/revoke-premium`);
  return res.data;
}

export async function fetchAdminPlans(includeInactive = true) {
  const res = await api.get('/api/admin/plans', {
    params: { include_inactive: includeInactive },
  });
  return res.data;
}

export async function createAdminPlan(body) {
  const res = await api.post('/api/admin/plans', body);
  return res.data;
}

export async function updateAdminPlan(planId, body) {
  const res = await api.put(`/api/admin/plans/${planId}`, body);
  return res.data;
}

export async function deleteAdminPlan(planId, { force = false } = {}) {
  const res = await api.delete(`/api/admin/plans/${planId}`, {
    params: { force },
  });
  return res.data;
}

export async function reorderAdminPlans(orderedIds) {
  const res = await api.put('/api/admin/plans/reorder', { ordered_ids: orderedIds });
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
