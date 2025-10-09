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

  // Generate detailed report
  generateDetailedReport: (testId) =>
    api.post(`/tests/${testId}/detailed-report`),

  // Get detailed report
  getDetailedReport: (testId) => api.get(`/tests/${testId}/detailed-report`),

  // Get report content
  getReportContent: (testId) => api.get(`/tests/${testId}/report-content`),
};

// Causal experiment API
export const causalExperimentApi = {
  // Run causal experiment
  runExperiment: (experimentData) => {
    console.log(
      "🌐 API: Calling /experiments/causal with data:",
      experimentData
    );
    return api.post("/experiments/causal", experimentData, { timeout: 300000 });
  },

  // Get experiment results
  getExperiment: (experimentId) => api.get(`/experiments/${experimentId}`),

  // List all experiments
  listExperiments: () => api.get("/experiments"),

  // Generate variations only (without running tests)
  generateVariations: (data) =>
    api.post("/experiments/generate-variations", data, { timeout: 60000 }),
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
