import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理token过期
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 话题相关API
export const topicsApi = {
  getAll: (params = {}) => api.get('/topics/', { params }),
  getById: (id) => api.get(`/topics/${id}`),
  create: (data) => api.post('/topics/', data),
  update: (id, data) => api.put(`/topics/${id}`, data),
  delete: (id) => api.delete(`/topics/${id}`),
  getCategories: () => api.get('/topics/categories/list'),
  getHot: (limit = 10) => api.get('/topics/hot/trending', { params: { limit } }),
};

// 辩论相关API
export const debatesApi = {
  getAll: (params = {}) => api.get('/debates/', { params }),
  getById: (id) => api.get(`/debates/${id}`),
  create: (data) => api.post('/debates/', data),
  start: (id) => api.post(`/debates/${id}/start`),
  update: (id, data) => api.put(`/debates/${id}`, data),
  getMessages: (id, params = {}) => api.get(`/debates/${id}/messages`, { params }),
  getActive: () => api.get('/debates/live/active'),
  getAvailableModels: () => api.get('/debates/available/models'),
};

// 投票相关API
export const votesApi = {
  create: (data) => api.post('/votes/', data),
  getByDebate: (debateId, params = {}) => api.get(`/votes/debate/${debateId}`, { params }),
  getResult: (debateId) => api.get(`/votes/debate/${debateId}/result`),
  getByUser: (userId, params = {}) => api.get(`/votes/user/${userId}`, { params }),
  delete: (id) => api.delete(`/votes/${id}`),
  getStatistics: () => api.get('/votes/statistics/overview'),
};

// 排行榜相关API
export const rankingsApi = {
  getOverall: (limit = 20) => api.get('/rankings/overall', { params: { limit } }),
  getByCategory: (category, limit = 20) => api.get(`/rankings/category/${category}`, { params: { limit } }),
  getModelStats: (modelId) => api.get(`/rankings/model/${modelId}`),
  getCategories: () => api.get('/rankings/categories/list'),
  getRising: (limit = 10) => api.get('/rankings/trending/rising', { params: { limit } }),
  compareModels: (modelIds) => api.get('/rankings/statistics/comparison', { params: { model_ids: modelIds.join(',') } }),
  getOverview: () => api.get('/rankings/statistics/overview'),
};

// 模型配置相关API
export const modelsApi = {
  getAll: () => api.get('/models/'),
  getById: (id) => api.get(`/models/${id}`),
  getPairs: () => api.get('/models/pairs/available'),
  getHealth: () => api.get('/models/status/health'),
  getConfigInfo: () => api.get('/models/config/info'),
};

// 认证相关API
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    transformRequest: [(data) => {
      const params = new URLSearchParams();
      params.append('username', data.username);
      params.append('password', data.password);
      return params;
    }],
  }),
  getCurrentUser: () => api.get('/auth/me'),
  updateCurrentUser: (data) => api.put('/auth/me', data),
  changePassword: (oldPassword, newPassword) => api.post('/auth/change-password', null, {
    params: { old_password: oldPassword, new_password: newPassword }
  }),
  getStatistics: () => api.get('/auth/statistics'),
};

export default api;
