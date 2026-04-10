import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  register: (data) => api.post("/api/auth/register", data),
  login: (data) => api.post("/api/auth/login", data),
  me: () => api.get("/api/auth/me"),
};

export const chatApi = {
  query: (data) => api.post("/api/chat/query", data),
  listConversations: () => api.get("/api/chat/conversations"),
  getConversation: (id) => api.get(`/api/chat/conversations/${id}`),
};

export const documentsApi = {
  list: () => api.get("/api/documents/"),
  upload: (formData) => api.post("/api/documents/upload", formData),
  delete: (id) => api.delete(`/api/documents/${id}`),
};

export const adminApi = {
  listUsers: () => api.get("/api/admin/users"),
  updateRole: (userId, role) => api.patch(`/api/admin/users/${userId}/role`, { role }),
  getAnalytics: () => api.get("/api/admin/analytics"),
  getAuditLogs: (params) => api.get("/api/admin/audit-logs", { params }),
  getDocumentAccess: (docId) => api.get(`/api/admin/document-access/${docId}`),
};

export default api;
