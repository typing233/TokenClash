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
  getConfiguredModels: () => api.get('/models/'),
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

// DNA指纹相关API
export const dnaApi = {
  getAllFingerprints: () => api.get('/dna/fingerprints'),
  getFingerprint: (modelId) => api.get(`/dna/fingerprints/${modelId}`),
  updateFingerprint: (data) => api.post('/dna/fingerprints/update', data),
  compareFingerprints: (model1Id, model2Id) => api.get(`/dna/compare/${model1Id}/${model2Id}`),
  getFingerprintAnalytics: (modelId) => api.get(`/dna/fingerprints/${modelId}/analytics`),
  getNebulaPattern: (modelId) => api.get(`/dna/nebula/${modelId}`),
  generateNebulaPattern: (modelId) => api.post(`/dna/nebula/${modelId}/generate`),
  getAllNebulaPatterns: () => api.get('/dna/nebula'),
  exportNebulaSvg: (modelId, width = 800, height = 600) => 
    api.get(`/dna/nebula/${modelId}/export/svg`, {
      params: { width, height },
      responseType: 'blob'
    }),
};

// 竞技场相关API
export const arenaApi = {
  getRooms: () => api.get('/arena/rooms'),
  getActiveRooms: () => api.get('/arena/rooms'),
  getRoom: (roomId) => api.get(`/arena/rooms/${roomId}`),
  createRoom: (data) => api.post('/arena/rooms', data),
  startRoom: (roomId) => api.post(`/arena/rooms/${roomId}/start`),
  getRoomHistory: () => api.get('/arena/rooms/history'),
  getSkills: () => api.get('/arena/skills'),
  useSkill: (roomId, data) => 
    api.post(`/arena/rooms/${roomId}/skills`, data),
  castVote: (roomId, data) => 
    api.post(`/arena/rooms/${roomId}/vote`, data),
  addEnergy: (roomId, data) => 
    api.post(`/arena/rooms/${roomId}/energy`, data),
};

// Token关系网络相关API
export const networkApi = {
  getGraph: () => api.get('/network/graph'),
  rebuildGraph: () => api.post('/network/graph/rebuild'),
  getNodeDetail: (modelId) => api.get(`/network/nodes/${modelId}`),
  getHiddenRelations: (limit = 20) => api.get('/network/adamic-adar', { params: { limit } }),
  getAdamicAdarPairs: (limit = 20) => api.get('/network/adamic-adar', { params: { limit } }),
  getRelationships: (modelId) => api.get(`/network/relationships/${modelId}`),
  buildFromDebates: () => api.post('/network/build'),
};

// LLM配置API（动态配置）
export const llmConfigApi = {
  getConfig: () => api.get('/llm-config'),
  updateConfig: (data) => api.post('/llm-config', data),
  testConnection: (config) => api.post('/llm-config/test', config),
  getModels: () => api.get('/llm-config/models'),
};

export default api;
