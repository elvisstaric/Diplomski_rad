<template>
  <div class="space-y-6">
    <!-- Test Results Header -->
    <div class="flex justify-between items-center">
      <h2 class="text-lg font-semibold text-gray-900">Test Results</h2>
    </div>

    <!-- Active Tests -->
    <div v-if="activeTests.length > 0" class="space-y-4">
      <h3 class="text-md font-medium text-gray-900">Active Tests</h3>
      <div
        v-for="test in activeTests"
        :key="test.test_id"
        class="card cursor-pointer hover:shadow-md transition-shadow duration-200"
        @click="openTestDetails(test)"
      >
        <div class="flex justify-between items-start mb-4">
          <div>
            <h4 class="font-medium text-gray-900">{{ test.test_id }}</h4>
            <p class="text-sm text-gray-500">
              Started: {{ formatDateTime(test.start_time) }}
            </p>
          </div>
          <span :class="getStatusBadgeClass(test.status)">
            {{ test.status }}
          </span>
        </div>

        <!-- Progress Bar -->
        <div class="mb-4">
          <div class="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{{ Math.round(test.progress) }}%</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              :class="getProgressBarClass(test.status)"
              :style="{ width: `${test.progress}%` }"
              class="h-2 rounded-full transition-all duration-300"
            ></div>
          </div>
        </div>

        <!-- Test Details -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span class="text-gray-500">Duration:</span>
            <span class="ml-2">{{ test.test_duration || "N/A" }}s</span>
          </div>
          <div>
            <span class="text-gray-500">Elapsed:</span>
            <span class="ml-2">{{ getElapsedTime(test.start_time) }}</span>
          </div>
          <div>
            <span class="text-gray-500">Status:</span>
            <span class="ml-2">{{ test.status }}</span>
          </div>
        </div>

        <!-- Error Message -->
        <div
          v-if="test.error"
          class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg"
        >
          <p class="text-sm text-red-800">{{ test.error }}</p>
        </div>
      </div>
    </div>

    <!-- Completed Tests -->
    <div v-if="completedTests.length > 0" class="space-y-4">
      <h3 class="text-md font-medium text-gray-900">Completed Tests</h3>
      <div
        v-for="test in completedTests"
        :key="test.test_id"
        class="card cursor-pointer hover:shadow-md transition-shadow duration-200"
        @click="openTestDetails(test)"
      >
        <div class="flex justify-between items-start mb-4">
          <div>
            <h4 class="font-medium text-gray-900">{{ test.test_id }}</h4>
            <p class="text-sm text-gray-500">
              Completed: {{ formatDateTime(test.end_time) }}
            </p>
          </div>
          <span :class="getStatusBadgeClass(test.status)">
            {{ test.status }}
          </span>
        </div>

        <!-- Test Results -->
        <div v-if="test.results" class="space-y-4">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="text-center p-3 bg-green-50 rounded-lg">
              <div class="text-2xl font-bold text-green-600">
                {{ test.results.successful_requests || 0 }}
              </div>
              <div class="text-sm text-green-800">Successful</div>
            </div>
            <div class="text-center p-3 bg-red-50 rounded-lg">
              <div class="text-2xl font-bold text-red-600">
                {{ test.results.failed_requests || 0 }}
              </div>
              <div class="text-sm text-red-800">Failed</div>
            </div>
            <div class="text-center p-3 bg-blue-50 rounded-lg">
              <div class="text-2xl font-bold text-blue-600">
                {{ test.results.total_requests || 0 }}
              </div>
              <div class="text-sm text-blue-800">Total</div>
            </div>
            <div class="text-center p-3 bg-purple-50 rounded-lg">
              <div class="text-2xl font-bold text-purple-600">
                {{
                  calculateDuration(
                    test.results.start_time,
                    test.results.end_time
                  )
                }}
              </div>
              <div class="text-sm text-purple-800">Duration</div>
            </div>
            <div class="text-center p-3 bg-green-50 rounded-lg">
              <div class="text-2xl font-bold text-green-600">
                {{ test.results.min_latency.toFixed(5) || 0 }}
              </div>
              <div class="text-sm text-green-800">Min Latency</div>
            </div>
            <div class="text-center p-3 bg-blue-50 rounded-lg">
              <div class="text-2xl font-bold text-blue-600">
                {{ test.results.avg_latency.toFixed(5) || 0 }}
              </div>
              <div class="text-sm text-blue-800">Average Latency</div>
            </div>
            <div class="text-center p-3 bg-red-50 rounded-lg">
              <div class="text-2xl font-bold text-red-600">
                {{ test.results.max_latency.toFixed(5) || 0 }}
              </div>
              <div class="text-sm text-red-800">Max Latency</div>
            </div>
          </div>

          <!-- Report Actions -->
          <div class="flex space-x-3 pt-4 border-t border-gray-200">
            <button
              @click="generateDetailedReport(test)"
              :disabled="isGeneratingReport"
              class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="isGeneratingReport">Generating Analysis...</span>
              <span v-else>Generate report</span>
            </button>

            <button
              v-if="test.hasReport"
              @click="viewReport(test)"
              class="btn-secondary"
            >
              View Report
            </button>

            <button
              v-if="test.hasReport"
              @click="downloadReport(test)"
              class="btn-secondary"
            >
              Download Markdown
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Failed Tests -->
    <div v-if="failedTests.length > 0" class="space-y-4">
      <h3 class="text-md font-medium text-gray-900">Failed Tests</h3>
      <div
        v-for="test in failedTests"
        :key="test.test_id"
        class="card border-red-200 bg-red-50 cursor-pointer hover:shadow-md transition-shadow duration-200"
        @click="openTestDetails(test)"
      >
        <div class="flex justify-between items-start mb-4">
          <div>
            <h4 class="font-medium text-red-900">{{ test.test_id }}</h4>
            <p class="text-sm text-red-700">
              Failed: {{ formatDateTime(test.end_time) }}
            </p>
          </div>
          <span
            class="px-2 py-1 text-xs font-medium text-red-800 bg-red-200 rounded-full"
          >
            {{ test.status }}
          </span>
        </div>

        <div
          v-if="test.error"
          class="p-3 bg-red-100 border border-red-300 rounded-lg"
        >
          <p class="text-sm text-red-800">{{ test.error }}</p>
        </div>

        <!-- Report Actions for Failed Tests -->
        <div
          v-if="test.results"
          class="flex space-x-3 pt-4 border-t border-red-200"
        >
          <button
            @click="generateDetailedReport(test)"
            :disabled="isGeneratingReport"
            class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isGeneratingReport">Generating Analysis...</span>
            <span v-else>Generate report</span>
          </button>

          <button
            v-if="test.hasReport"
            @click="viewReport(test)"
            class="btn-secondary"
          >
            View Report
          </button>

          <button
            v-if="test.hasReport"
            @click="downloadReport(test)"
            class="btn-secondary"
          >
            Download Markdown
          </button>
        </div>
      </div>
    </div>

    <!-- No Tests Message -->
    <div v-if="tests.length === 0" class="text-center py-12">
      <svg
        class="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        ></path>
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No tests found</h3>
      <p class="mt-1 text-sm text-gray-500">
        Start a new test to see results here.
      </p>
    </div>

    <!-- Test Details Modal -->
    <div
      v-if="selectedTest"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden"
      >
        <div
          class="flex justify-between items-center p-4 border-b border-gray-200"
        >
          <h3 class="text-lg font-semibold">
            Test Details: {{ selectedTest.test_id }}
          </h3>
          <button
            @click="selectedTest = null"
            class="text-gray-400 hover:text-gray-600"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <div class="p-4 overflow-y-auto max-h-[70vh]">
          <!-- Test Configuration -->
          <div class="space-y-6">
            <!-- Basic Info -->
            <div>
              <h4 class="font-medium text-gray-900 mb-3">Basic Information</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span class="text-gray-500">Test ID:</span>
                  <span class="ml-2 font-mono">{{ selectedTest.test_id }}</span>
                </div>
                <div>
                  <span class="text-gray-500">Status:</span>
                  <span
                    :class="getStatusBadgeClass(selectedTest.status)"
                    class="ml-2 px-2 py-1 text-xs font-medium rounded-full"
                  >
                    {{ selectedTest.status }}
                  </span>
                </div>
                <div>
                  <span class="text-gray-500">Start Time:</span>
                  <span class="ml-2">{{
                    formatDateTime(selectedTest.start_time)
                  }}</span>
                </div>
                <div v-if="selectedTest.end_time">
                  <span class="text-gray-500">End Time:</span>
                  <span class="ml-2">{{
                    formatDateTime(selectedTest.end_time)
                  }}</span>
                </div>
                <div>
                  <span class="text-gray-500">Progress:</span>
                  <span class="ml-2"
                    >{{ Math.round(selectedTest.progress) }}%</span
                  >
                </div>
                <div v-if="selectedTest.test_duration">
                  <span class="text-gray-500">Duration:</span>
                  <span class="ml-2">{{ selectedTest.test_duration }}s</span>
                </div>
              </div>
            </div>

            <!-- DSL Script -->
            <div v-if="selectedTest.dsl_script">
              <h4 class="font-medium text-gray-900 mb-3">DSL Script</h4>
              <div class="bg-gray-100 rounded-lg p-4">
                <pre
                  class="text-sm font-mono whitespace-pre-wrap overflow-x-auto"
                  >{{ selectedTest.dsl_script }}</pre
                >
              </div>
            </div>

            <!-- Target URL -->
            <div v-if="selectedTest.target_url">
              <h4 class="font-medium text-gray-900 mb-3">Target URL</h4>
              <div class="bg-gray-100 rounded-lg p-3">
                <code class="text-sm">{{ selectedTest.target_url }}</code>
              </div>
            </div>

            <!-- Swagger Docs -->
            <div v-if="selectedTest.swagger_docs">
              <h4 class="font-medium text-gray-900 mb-3">
                Swagger Documentation
              </h4>
              <div class="bg-gray-100 rounded-lg p-4 max-h-40 overflow-y-auto">
                <pre class="text-sm font-mono whitespace-pre-wrap">{{
                  selectedTest.swagger_docs
                }}</pre>
              </div>
            </div>

            <!-- Auth Credentials -->
            <div
              v-if="
                selectedTest.auth_credentials &&
                Object.keys(selectedTest.auth_credentials).length > 0
              "
            >
              <h4 class="font-medium text-gray-900 mb-3">Authentication</h4>
              <div class="bg-gray-100 rounded-lg p-3">
                <div class="text-sm">
                  <div v-if="selectedTest.auth_credentials.username">
                    <span class="text-gray-500">Username:</span>
                    <span class="ml-2 font-mono">{{
                      selectedTest.auth_credentials.username
                    }}</span>
                  </div>
                  <div v-if="selectedTest.auth_credentials.password">
                    <span class="text-gray-500">Password:</span>
                    <span class="ml-2 font-mono">••••••••</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Error Message -->
            <div v-if="selectedTest.error">
              <h4 class="font-medium text-red-900 mb-3">Error</h4>
              <div class="bg-red-50 border border-red-200 rounded-lg p-3">
                <p class="text-sm text-red-800">{{ selectedTest.error }}</p>
              </div>
            </div>

            <!-- Error Details -->
            <div
              v-if="
                selectedTest.results &&
                selectedTest.results.error_details &&
                selectedTest.results.error_details.length > 0
              "
              class="space-y-3"
            >
              <h4 class="font-medium text-red-900">Error Details</h4>
              <div class="space-y-3 max-h-60 overflow-y-auto">
                <div
                  v-for="(error, index) in selectedTest.results.error_details"
                  :key="index"
                  class="p-4 bg-red-50 border border-red-200 rounded-lg"
                >
                  <!-- Error Header -->
                  <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center space-x-2">
                      <span
                        :class="getErrorCategoryClass(error.category)"
                        class="px-2 py-1 text-xs font-medium rounded-full"
                      >
                        {{ error.category || "unknown" }}
                      </span>
                      <span
                        :class="getErrorSeverityClass(error.severity)"
                        class="px-2 py-1 text-xs font-medium rounded-full"
                      >
                        {{ error.severity || "low" }}
                      </span>
                    </div>
                    <span class="text-xs text-gray-500">
                      User {{ error.user_id || "N/A" }}
                    </span>
                  </div>

                  <!-- Error Message -->
                  <div class="text-sm text-red-800 mb-2">
                    {{ error.error_message || error }}
                  </div>

                  <!-- Error Metadata -->
                  <div class="grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <div>
                      <span class="font-medium">Endpoint:</span>
                      <span class="ml-1 font-mono">{{
                        error.endpoint || "N/A"
                      }}</span>
                    </div>
                    <div>
                      <span class="font-medium">Attempt:</span>
                      <span class="ml-1">{{ error.attempt || "N/A" }}</span>
                    </div>
                    <div>
                      <span class="font-medium">Time:</span>
                      <span class="ml-1">{{
                        formatErrorTime(error.timestamp)
                      }}</span>
                    </div>
                    <div>
                      <span class="font-medium">Retry Eligible:</span>
                      <span class="ml-1">{{
                        error.retry_eligible ? "Yes" : "No"
                      }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end p-4 border-t border-gray-200">
          <button @click="selectedTest = null" class="btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Report Modal -->
    <div
      v-if="showReportModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden"
      >
        <div
          class="flex justify-between items-center p-4 border-b border-gray-200"
        >
          <h3 class="text-lg font-semibold">
            Detailed Test Report: {{ selectedReportTest?.test_id }}
          </h3>
          <div class="flex space-x-2">
            <button
              @click="downloadReport(selectedReportTest)"
              class="btn-secondary text-sm"
            >
              Download Markdown
            </button>
            <button
              @click="showReportModal = false"
              class="text-gray-400 hover:text-gray-600"
            >
              <svg
                class="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                ></path>
              </svg>
            </button>
          </div>
        </div>

        <div class="p-4 overflow-y-auto max-h-[80vh]">
          <div v-if="isGeneratingReport" class="text-center py-8">
            <div
              class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"
            ></div>
            <p class="mt-4 text-gray-600">Generating detailed report...</p>
          </div>

          <div v-else-if="reportContent" class="prose max-w-none">
            <pre
              class="whitespace-pre-wrap text-sm font-mono bg-gray-50 p-4 rounded-lg"
              >{{ reportContent }}</pre
            >
          </div>

          <div v-else class="text-center py-8 text-gray-500">
            <p>No report content available</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from "vue";
import { testApi, causalExperimentApi } from "../services/api";

export default {
  name: "TestResults",
  props: {
    tests: {
      type: Array,
      default: () => [],
    },
    isRefreshing: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["refresh-tests"],
  setup(props) {
    const selectedTest = ref(null);
    const showReportModal = ref(false);
    const selectedReportTest = ref(null);
    const reportContent = ref("");
    const isGeneratingReport = ref(false);

    const openTestDetails = (test) => {
      selectedTest.value = test;
    };
    const activeTests = computed(() =>
      props.tests.filter(
        (test) => test.status === "running" || test.status === "pending"
      )
    );

    const completedTests = computed(() =>
      props.tests.filter((test) => test.status === "completed")
    );

    const failedTests = computed(() =>
      props.tests.filter((test) => test.status === "failed")
    );

    const formatDateTime = (dateString) => {
      if (!dateString) return "N/A";
      return new Date(dateString).toLocaleString();
    };

    const getElapsedTime = (startTime) => {
      if (!startTime) return "N/A";
      const start = new Date(startTime);
      const now = new Date();
      const elapsed = Math.floor((now - start) / 1000);

      if (elapsed < 60) return `${elapsed}s`;
      if (elapsed < 3600)
        return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
      return `${Math.floor(elapsed / 3600)}h ${Math.floor(
        (elapsed % 3600) / 60
      )}m`;
    };

    const formatDuration = (seconds) => {
      if (!seconds) return "N/A";
      if (seconds < 60) return `${seconds}s`;
      if (seconds < 3600)
        return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
      return `${Math.floor(seconds / 3600)}h ${Math.floor(
        (seconds % 3600) / 60
      )}m`;
    };

    const calculateDuration = (startTime, endTime) => {
      if (!startTime || !endTime) return "N/A";

      const start = new Date(startTime);
      const end = new Date(endTime);
      const durationMs = end - start;
      const durationSeconds = Math.floor(durationMs / 1000);

      return formatDuration(durationSeconds);
    };

    const getStatusBadgeClass = (status) => {
      const baseClasses = "px-2 py-1 text-xs font-medium rounded-full";

      switch (status) {
        case "pending":
          return `${baseClasses} text-yellow-800 bg-yellow-200`;
        case "running":
          return `${baseClasses} text-blue-800 bg-blue-200`;
        case "completed":
          return `${baseClasses} text-green-800 bg-green-200`;
        case "failed":
          return `${baseClasses} text-red-800 bg-red-200`;
        default:
          return `${baseClasses} text-gray-800 bg-gray-200`;
      }
    };

    const getProgressBarClass = (status) => {
      switch (status) {
        case "pending":
          return "bg-yellow-500";
        case "running":
          return "bg-blue-500";
        case "completed":
          return "bg-green-500";
        case "failed":
          return "bg-red-500";
        default:
          return "bg-gray-500";
      }
    };

    const getErrorCategoryClass = (category) => {
      const baseClasses = "px-2 py-1 text-xs font-medium rounded-full";
      switch (category) {
        case "timeout":
          return `${baseClasses} text-orange-800 bg-orange-200`;
        case "network":
          return `${baseClasses} text-purple-800 bg-purple-200`;
        case "http_error":
          return `${baseClasses} text-blue-800 bg-blue-200`;
        case "auth_error":
          return `${baseClasses} text-red-800 bg-red-200`;
        case "server_error":
          return `${baseClasses} text-red-800 bg-red-200`;
        default:
          return `${baseClasses} text-gray-800 bg-gray-200`;
      }
    };

    const getErrorSeverityClass = (severity) => {
      const baseClasses = "px-2 py-1 text-xs font-medium rounded-full";
      switch (severity) {
        case "low":
          return `${baseClasses} text-green-800 bg-green-200`;
        case "medium":
          return `${baseClasses} text-yellow-800 bg-yellow-200`;
        case "high":
          return `${baseClasses} text-orange-800 bg-orange-200`;
        case "critical":
          return `${baseClasses} text-red-800 bg-red-200`;
        default:
          return `${baseClasses} text-gray-800 bg-gray-200`;
      }
    };

    const formatErrorTime = (timestamp) => {
      if (!timestamp) return "N/A";
      try {
        return new Date(timestamp).toLocaleString();
      } catch (e) {
        return timestamp;
      }
    };

    const generateDetailedReport = async (test) => {
      if (!test || (test.status !== "completed" && test.status !== "failed")) {
        alert("Analysis can only be generated for completed or failed tests");
        return;
      }

      isGeneratingReport.value = true;
      selectedReportTest.value = test;
      showReportModal.value = true;
      reportContent.value = "";

      try {
        const response = await testApi.generateDetailedReport(test.test_id);
        reportContent.value = response.data.report_content;
        test.hasReport = true;
        test.reportContent = response.data.report_content; // Store in test object for download
      } catch (error) {
        alert(
          "Error generating detailed report: " +
            (error.response?.data?.detail || error.message)
        );
      } finally {
        isGeneratingReport.value = false;
      }
    };

    const viewReport = (test) => {
      if (test.hasReport) {
        selectedReportTest.value = test;
        showReportModal.value = true;
        reportContent.value = test.reportContent || "";
      }
    };

    const downloadReport = (test) => {
      if (test.hasReport) {
        // Use reportContent from the modal if available, otherwise use test.reportContent
        const content = reportContent.value || test.reportContent || "";
        if (content) {
          const blob = new Blob([content], { type: "text/markdown" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `test-report-${test.test_id}.md`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        } else {
          alert("No report content available to download");
        }
      } else {
        alert("No report available for this test");
      }
    };

    return {
      selectedTest,
      openTestDetails,
      activeTests,
      completedTests,
      failedTests,
      formatDateTime,
      getElapsedTime,
      formatDuration,
      calculateDuration,
      getStatusBadgeClass,
      getProgressBarClass,
      getErrorCategoryClass,
      getErrorSeverityClass,
      formatErrorTime,
      // Report functionality
      showReportModal,
      selectedReportTest,
      reportContent,
      isGeneratingReport,
      generateDetailedReport,
      viewReport,
      downloadReport,
    };
  },
};
</script>
