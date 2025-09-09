import axios from "axios";

const API_BASE_URL = "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Test management
export const testApi = {
  // Create a new test
  createTest: (testData) => api.post("/tests", testData),

  // Get test status
  getTestStatus: (testId) => api.get(`/tests/${testId}`),

  // List all tests
  listTests: () => api.get("/tests"),

  // Delete test
  deleteTest: (testId) => api.delete(`/tests/${testId}`),

  // Ping backend
  pingBackend: (url) => api.post("/ping", { url }),
};

// DSL management
export const dslApi = {
  // Generate DSL from description
  generateDsl: (data) => api.post("/generate-dsl", data),

  // Optimize existing DSL
  optimizeDsl: (data) => api.post("/optimize-dsl", data),

  // Validate DSL
  validateDsl: (dslScript) =>
    api.post("/validate-dsl", dslScript, {
      headers: { "Content-Type": "text/plain" },
    }),
};

export default api;
