<template>
  <div class="max-w-4xl mx-auto p-6">
    <h2 class="text-2xl font-bold mb-6">Causal Inference Experiment</h2>

    <!-- Experiment Form -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4">Configure Experiment</h3>

      <div class="space-y-4">
        <!-- Baseline DSL -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Baseline DSL Script
          </label>
          <textarea
            v-model="experimentForm.baselineDsl"
            class="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="users: 10&#10;pattern: steady&#10;duration: 60&#10;journey:&#10;  - step: login&#10;    endpoint: /login&#10;    method: POST"
          ></textarea>
        </div>

        <!-- Experiment Description -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            What do you want to test?
          </label>
          <textarea
            v-model="experimentForm.experimentDescription"
            class="w-full h-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Test impact of user load on API performance"
          ></textarea>
        </div>

        <!-- Number of Tests -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Number of Test Variations
          </label>
          <select
            v-model="experimentForm.numberOfTests"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="3">3 tests</option>
            <option value="4">4 tests</option>
            <option value="5">5 tests</option>
            <option value="6">6 tests</option>
          </select>
        </div>

        <!-- Target URL -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Target URL
          </label>
          <input
            v-model="experimentForm.targetUrl"
            type="url"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="https://api.example.com"
          />
        </div>

        <!-- Run Experiment Button -->
        <div class="pt-4">
          <button
            @click="runExperiment"
            :disabled="isRunningExperiment"
            class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            <span v-if="isRunningExperiment">Running Experiment...</span>
            <span v-else>Run Causal Experiment</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Experiment Results -->
    <div v-if="currentExperiment" class="bg-white rounded-lg shadow-md p-6">
      <h3 class="text-lg font-semibold mb-4">Experiment Results</h3>

      <!-- Experiment Summary -->
      <div class="mb-6 p-4 bg-gray-50 rounded-md">
        <h4 class="font-medium mb-2">Experiment Summary</h4>
        <p><strong>ID:</strong> {{ currentExperiment.experiment_id }}</p>
        <p>
          <strong>Description:</strong>
          {{ experimentForm.experimentDescription }}
        </p>
        <p>
          <strong>Number of Tests:</strong>
          {{ currentExperiment.test_results.length }}
        </p>
        <p><strong>Completed:</strong> {{ currentExperiment.generated_at }}</p>
      </div>

      <!-- Test Results Table -->
      <div class="mb-6">
        <h4 class="font-medium mb-3">Test Results</h4>
        <div class="overflow-x-auto">
          <table class="min-w-full table-auto">
            <thead>
              <tr class="bg-gray-50">
                <th class="px-4 py-2 text-left">Variation</th>
                <th class="px-4 py-2 text-left">Status</th>
                <th class="px-4 py-2 text-left">Requests</th>
                <th class="px-4 py-2 text-left">Success Rate</th>
                <th class="px-4 py-2 text-left">Avg Latency</th>
                <th class="px-4 py-2 text-left">Latency Variance</th>
                <th class="px-4 py-2 text-left">Error Rate</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="result in currentExperiment.test_results"
                :key="result.test_id"
                class="border-t"
              >
                <td class="px-4 py-2">{{ result.variation_name }}</td>
                <td class="px-4 py-2">
                  <span :class="getStatusClass(result.status)">
                    {{ result.status }}
                  </span>
                </td>
                <td class="px-4 py-2">{{ result.total_requests }}</td>
                <td class="px-4 py-2">{{ result.success_rate }}%</td>
                <td class="px-4 py-2">
                  {{ (result.avg_latency || 0).toFixed(2) }}ms
                </td>
                <td class="px-4 py-2">
                  {{ (result.latency_variance || 0).toFixed(2) }}ms²
                </td>
                <td class="px-4 py-2">{{ result.failure_rate }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Causal Analysis -->
      <div class="mb-6">
        <h4 class="font-medium mb-3">Causal Analysis</h4>
        <div class="bg-gray-50 p-4 rounded-md">
          <pre class="whitespace-pre-wrap text-sm">{{
            currentExperiment.causal_analysis
          }}</pre>
        </div>
      </div>

      <!-- Download Report -->
      <div class="flex space-x-4">
        <button
          @click="downloadCausalReport"
          class="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700"
        >
          Download Causal Report
        </button>
        <button
          @click="viewCausalReport"
          class="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
        >
          View Full Report
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isRunningExperiment" class="bg-white rounded-lg shadow-md p-6">
      <div class="text-center">
        <div
          class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"
        ></div>
        <p class="text-gray-600">Running causal experiment...</p>
        <p class="text-sm text-gray-500 mt-2">This may take several minutes</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="bg-red-50 border border-red-200 rounded-md p-4">
      <p class="text-red-800">{{ error }}</p>
    </div>
  </div>
</template>

<script>
import { causalExperimentApi } from "../services/api.js";

export default {
  name: "CausalExperiment",
  data() {
    return {
      experimentForm: {
        baselineDsl: "",
        experimentDescription: "",
        numberOfTests: 4,
        targetUrl: "",
      },
      currentExperiment: null,
      isRunningExperiment: false,
      error: null,
    };
  },
  methods: {
    async runExperiment() {
      if (!this.validateForm()) {
        return;
      }

      this.isRunningExperiment = true;
      this.error = null;
      this.currentExperiment = null;

      try {
        const experimentData = {
          baseline_dsl: this.experimentForm.baselineDsl,
          experiment_description: this.experimentForm.experimentDescription,
          number_of_tests: parseInt(this.experimentForm.numberOfTests),
          target_url: this.experimentForm.targetUrl,
          auth_credentials: {},
        };

        const response = await causalExperimentApi.runExperiment(
          experimentData
        );
        this.currentExperiment = response.data;
      } catch (error) {
        console.error("Error running experiment:", error);
        this.error = error.response?.data?.detail || "Failed to run experiment";
      } finally {
        this.isRunningExperiment = false;
      }
    },

    validateForm() {
      if (!this.experimentForm.baselineDsl.trim()) {
        this.error = "Baseline DSL is required";
        return false;
      }

      if (!this.experimentForm.experimentDescription.trim()) {
        this.error = "Experiment description is required";
        return false;
      }

      if (!this.experimentForm.targetUrl.trim()) {
        this.error = "Target URL is required";
        return false;
      }

      return true;
    },

    getStatusClass(status) {
      switch (status) {
        case "completed":
          return "text-green-600 font-medium";
        case "failed":
          return "text-red-600 font-medium";
        case "timeout":
          return "text-yellow-600 font-medium";
        default:
          return "text-gray-600";
      }
    },

    downloadCausalReport() {
      if (!this.currentExperiment) return;

      const reportContent = this.generateCausalReport();
      const blob = new Blob([reportContent], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `causal-experiment-${this.currentExperiment.experiment_id}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },

    viewCausalReport() {
      if (!this.currentExperiment) return;

      const reportContent = this.generateCausalReport();
      const newWindow = window.open("", "_blank");
      newWindow.document.write(`
        <html>
          <head>
            <title>Causal Experiment Report</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 40px; }
              pre { white-space: pre-wrap; }
            </style>
          </head>
          <body>
            <pre>${reportContent}</pre>
          </body>
        </html>
      `);
    },

    generateCausalReport() {
      if (!this.currentExperiment) return "";

      const exp = this.currentExperiment;
      let report = `# Causal Inference Experiment Report\n\n`;

      report += `**Experiment ID:** ${exp.experiment_id}\n`;
      report += `**Description:** ${this.experimentForm.experimentDescription}\n`;
      report += `**Generated:** ${exp.generated_at}\n\n`;

      report += `## Baseline DSL\n\`\`\`dsl\n${exp.baseline_dsl}\n\`\`\`\n\n`;

      report += `## Test Results\n\n`;
      exp.test_results.forEach((result, index) => {
        report += `### Test ${index + 1}: ${result.variation_name}\n`;
        report += `- **Status:** ${result.status}\n`;
        report += `- **Total Requests:** ${result.total_requests}\n`;
        report += `- **Success Rate:** ${result.success_rate}%\n`;
        report += `- **Average Latency:** ${result.avg_latency}s\n`;
        report += `- **Error Rate:** ${result.failure_rate}%\n\n`;
      });

      report += `## Causal Analysis\n\n${exp.causal_analysis}\n\n`;

      return report;
    },
  },
};
</script>
