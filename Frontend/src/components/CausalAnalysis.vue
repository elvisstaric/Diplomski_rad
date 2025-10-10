<template>
  <div class="space-y-6">
    <!-- Saved Causal Experiments -->
    <div
      v-if="savedExperiments.length > 0"
      class="bg-white rounded-lg shadow p-6"
    >
      <h2 class="text-xl font-semibold text-gray-900 mb-4">
        Saved Causal Experiments
      </h2>
      <div class="space-y-4">
        <div
          v-for="experiment in savedExperiments"
          :key="experiment.experiment_id"
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
          @click="viewSavedExperiment(experiment)"
        >
          <div class="flex justify-between items-start">
            <div>
              <h3 class="font-medium text-gray-900">
                {{ experiment.experiment_id }}
              </h3>
              <p class="text-sm text-gray-500">
                Created: {{ formatDateTime(experiment.generated_at) }}
              </p>
              <p class="text-sm text-gray-500">
                Tests: {{ experiment.number_of_tests }}
              </p>
            </div>
            <span
              class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full"
            >
              Saved
            </span>
          </div>
          <div class="mt-2">
            <p class="text-sm text-gray-600 truncate">
              {{ experiment.baseline_dsl }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">Causal Analysis</h2>

      <!-- Test Selection -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Select Test for Analysis
        </label>
        <select
          v-model="selectedTestId"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Choose a test for analysis...</option>
          <optgroup label="Completed Tests">
            <option
              v-for="test in completedTests"
              :key="test.test_id"
              :value="test.test_id"
            >
              {{ test.test_id }} - {{ test.status }} ({{
                formatDateTime(test.start_time)
              }})
            </option>
          </optgroup>
          <optgroup label="Failed Tests">
            <option
              v-for="test in failedTests"
              :key="test.test_id"
              :value="test.test_id"
            >
              {{ test.test_id }} - {{ test.status }} ({{
                formatDateTime(test.start_time)
              }})
            </option>
          </optgroup>
        </select>
      </div>

      <!-- Experiment Configuration -->
      <div v-if="selectedTest" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Experiment Description
          </label>
          <textarea
            v-model="experimentDescription"
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Describe what you want to test (e.g., 'Test the impact of increased load on response time')"
          ></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Number of Test Variations
          </label>
          <select
            v-model="numberOfTests"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="2">2 tests</option>
            <option value="3">3 tests</option>
            <option value="4">4 tests</option>
            <option value="5">5 tests</option>
            <option value="6">6 tests</option>
            <option value="7">7 tests</option>
            <option value="8">8 tests</option>
            <option value="9">9 tests</option>
            <option value="10">10 tests</option>
          </select>
        </div>

        <!-- Generated DSL Variations -->
        <div
          v-if="generatedVariations.length > 0"
          class="bg-white p-6 rounded-lg shadow-md space-y-4"
        >
          <h3 class="text-lg font-semibold text-gray-900">
            Generated DSL Variations
          </h3>
          <div class="space-y-4">
            <div
              v-for="(variation, index) in generatedVariations"
              :key="index"
              class="border border-gray-200 rounded-lg p-4"
            >
              <div class="flex justify-between items-start mb-2">
                <h4 class="font-medium text-gray-800">
                  {{ variation.variation_name }}
                </h4>
                <button
                  @click="toggleVariation(index)"
                  class="text-blue-600 hover:text-blue-800 text-sm"
                >
                  {{ expandedVariations[index] ? "Hide DSL" : "Show DSL" }}
                </button>
              </div>
              <p class="text-sm text-gray-600 mb-2">
                {{ variation.description }}
              </p>
              <div v-if="expandedVariations[index]" class="mt-3">
                <pre class="bg-gray-100 p-3 rounded text-xs overflow-x-auto">{{
                  variation.dsl_script
                }}</pre>
              </div>
            </div>
          </div>

          <!-- Show All DSLs Button -->
          <div class="flex justify-center pt-4">
            <button
              @click="toggleAllVariations"
              class="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              {{ allExpanded ? "Hide All DSLs" : "Show All DSLs" }}
            </button>
          </div>
        </div>

        <div class="flex justify-end space-x-3">
          <button
            @click="generateVariations"
            :disabled="!canRunExperiment || isGeneratingVariations"
            class="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <svg
              v-if="isGeneratingVariations"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            {{
              isGeneratingVariations ? "Generating..." : "Generate Variations"
            }}
          </button>
          <button
            @click="runCausalExperiment"
            :disabled="
              !canRunExperiment ||
              generatedVariations.length === 0 ||
              isRunningExperiment
            "
            @mouseover="
              console.log(
                'Button hover - canRun:',
                canRunExperiment,
                'variations:',
                generatedVariations.length,
                'running:',
                isRunningExperiment
              )
            "
            class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <svg
              v-if="isRunningExperiment"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            {{
              isRunningExperiment
                ? "Running Analysis..."
                : "Run Causal Experiment"
            }}
          </button>
        </div>
      </div>
    </div>

    <!-- Results Modal -->
    <div
      v-if="showResultsModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden"
      >
        <div
          class="flex justify-between items-center p-4 border-b border-gray-200"
        >
          <h3 class="text-lg font-semibold text-gray-900">
            Causal Analysis Results
          </h3>
          <div class="flex items-center space-x-2">
            <button
              @click="downloadCausalReport"
              class="btn-secondary text-sm flex items-center space-x-2"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                ></path>
              </svg>
              <span>Download Markdown</span>
            </button>
            <button
              @click="showResultsModal = false"
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

        <div class="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div v-if="experimentResult" class="space-y-6">
            <!-- Causal Analysis Report -->
            <div class="bg-white border border-gray-200 rounded-lg p-6">
              <div
                class="prose prose-sm max-w-none"
                v-html="formatMarkdown(experimentResult.causal_analysis)"
              ></div>
            </div>

            <!-- Test Results Table -->
            <div>
              <h4 class="font-semibold text-gray-900 mb-3">Test Results</h4>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Test
                      </th>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Status
                      </th>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Success Rate
                      </th>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Avg Latency
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr
                      v-for="(result, index) in experimentResult.test_results"
                      :key="index"
                    >
                      <td
                        class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                      >
                        {{ result.variation_name || `Test ${index + 1}` }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span :class="getStatusClass(result.status)">
                          {{ result.status }}
                        </span>
                      </td>
                      <td
                        class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                      >
                        {{ result.success_rate }}%
                      </td>
                      <td
                        class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                      >
                        {{ result.avg_latency }}ms
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Saved Experiment Modal -->
    <div
      v-if="showSavedExperimentModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div class="p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold text-gray-900">
              Causal Analysis Results -
              {{ selectedSavedExperiment?.experiment_id }}
            </h3>
            <button
              @click="showSavedExperimentModal = false"
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

          <div v-if="selectedSavedExperiment" class="space-y-6">
            <!-- Experiment Info -->
            <div class="bg-gray-50 p-4 rounded-lg">
              <h4 class="font-medium text-gray-900 mb-2">Experiment Details</h4>
              <p class="text-sm text-gray-600">
                <strong>Created:</strong>
                {{ formatDateTime(selectedSavedExperiment.generated_at) }}
              </p>
              <p class="text-sm text-gray-600">
                <strong>Number of Tests:</strong>
                {{ selectedSavedExperiment.number_of_tests }}
              </p>
              <p class="text-sm text-gray-600">
                <strong>Description:</strong>
                {{ selectedSavedExperiment.description }}
              </p>
            </div>

            <!-- Causal Report -->
            <div
              v-if="selectedSavedExperiment.causal_analysis"
              class="space-y-4"
            >
              <div class="flex justify-between items-center">
                <h4 class="font-medium text-gray-900">
                  Causal Analysis Report
                </h4>
                <button
                  @click="downloadSavedCausalReport(selectedSavedExperiment)"
                  class="btn-secondary text-sm flex items-center space-x-2"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    ></path>
                  </svg>
                  <span>Download Report</span>
                </button>
              </div>
              <div class="bg-white border rounded-lg p-4">
                <div
                  v-html="
                    formatMarkdown(selectedSavedExperiment.causal_analysis)
                  "
                  class="prose max-w-none"
                ></div>
              </div>
            </div>

            <!-- Test Results Summary -->
            <div v-if="selectedSavedExperiment.test_results" class="space-y-4">
              <h4 class="font-medium text-gray-900">Test Results Summary</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div
                  v-for="(
                    result, index
                  ) in selectedSavedExperiment.test_results"
                  :key="index"
                  class="bg-gray-50 p-4 rounded-lg"
                >
                  <h5 class="font-medium text-gray-900 mb-2">
                    {{ result.variation_name }}
                  </h5>
                  <div class="space-y-1 text-sm">
                    <p><strong>Status:</strong> {{ result.status }}</p>
                    <p>
                      <strong>Total Requests:</strong>
                      {{ result.total_requests }}
                    </p>
                    <p>
                      <strong>Success Rate:</strong> {{ result.success_rate }}%
                    </p>
                    <p>
                      <strong>Avg Latency:</strong>
                      {{ result.avg_latency?.toFixed(3) }}s
                    </p>
                    <p>
                      <strong>Failure Rate:</strong> {{ result.failure_rate }}%
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onActivated, onUnmounted } from "vue";
import { causalExperimentApi } from "../services/api";

export default {
  name: "CausalAnalysis",
  props: {
    tests: {
      type: Array,
      default: () => [],
    },
  },
  setup(props) {
    const selectedTestId = ref("");
    const experimentDescription = ref("");
    const numberOfTests = ref(4);
    const showResultsModal = ref(false);
    const experimentResult = ref(null);
    const generatedVariations = ref([]);
    const expandedVariations = ref({});
    const allExpanded = ref(false);
    const isGeneratingVariations = ref(false);
    const isRunningExperiment = ref(false);

    // Saved experiments
    const savedExperiments = ref([]);
    const showSavedExperimentModal = ref(false);
    const selectedSavedExperiment = ref(null);

    const completedTests = computed(() => {
      const completed = props.tests.filter(
        (test) => test.status === "completed"
      );
      console.log(
        "completedTests computed - total tests:",
        props.tests.length,
        "completed:",
        completed.length
      );
      console.log(
        "All test statuses:",
        props.tests.map((t) => ({ id: t.test_id, status: t.status }))
      );
      return completed;
    });

    const failedTests = computed(() => {
      return props.tests.filter((test) => test.status === "failed");
    });

    const selectedTest = computed(() =>
      props.tests.find((test) => test.test_id === selectedTestId.value)
    );

    const canRunExperiment = computed(() => {
      const canRun = selectedTestId.value && experimentDescription.value.trim();
      console.log(
        "canRunExperiment computed - selectedTestId:",
        selectedTestId.value,
        "description:",
        experimentDescription.value.trim(),
        "result:",
        canRun
      );
      return canRun;
    });

    const formatDateTime = (dateString) => {
      if (!dateString) return "N/A";
      return new Date(dateString).toLocaleString();
    };

    const getStatusClass = (status) => {
      switch (status) {
        case "completed":
          return "inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800";
        case "failed":
          return "inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800";
        default:
          return "inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800";
      }
    };

    const toggleVariation = (index) => {
      expandedVariations.value[index] = !expandedVariations.value[index];
    };

    const toggleAllVariations = () => {
      allExpanded.value = !allExpanded.value;
      generatedVariations.value.forEach((_, index) => {
        expandedVariations.value[index] = allExpanded.value;
      });
    };

    const generateVariations = async () => {
      if (!selectedTest.value) {
        alert("Please select a test");
        return;
      }

      try {
        isGeneratingVariations.value = true;

        const experimentData = {
          baseline_dsl:
            selectedTest.value.dsl_script ||
            selectedTest.value.dsl ||
            selectedTest.value.script ||
            "",
          experiment_description: experimentDescription.value,
          number_of_tests: numberOfTests.value,
          target_url:
            selectedTest.value.target_url || selectedTest.value.url || "",
          auth_type: selectedTest.value.auth_type || "none",
          auth_credentials: selectedTest.value.auth_credentials || {},
        };

        const response = await causalExperimentApi.generateVariations(
          experimentData
        );
        generatedVariations.value = response.data.variations;

        // Initialize expandedVariations
        expandedVariations.value = {};
        generatedVariations.value.forEach((_, index) => {
          expandedVariations.value[index] = false;
        });
      } catch (error) {
        alert(
          "Error generating variations: " +
            (error.response?.data?.detail || error.message)
        );
      } finally {
        isGeneratingVariations.value = false;
      }
    };

    const runCausalExperiment = async () => {
      console.log("🎯 runCausalExperiment called!");
      console.log("Selected test:", selectedTest.value);
      console.log("Can run experiment:", canRunExperiment.value);
      console.log("Generated variations:", generatedVariations.value.length);

      if (!selectedTest.value) {
        alert("Please select a test");
        return;
      }

      try {
        isRunningExperiment.value = true;

        const experimentData = {
          baseline_dsl:
            selectedTest.value.dsl_script ||
            selectedTest.value.dsl ||
            selectedTest.value.script ||
            "",
          experiment_description: experimentDescription.value,
          number_of_tests: numberOfTests.value,
          target_url:
            selectedTest.value.target_url || selectedTest.value.url || "",
          auth_type: selectedTest.value.auth_type || "none",
          auth_credentials: selectedTest.value.auth_credentials || {},
          generated_variations: generatedVariations.value, // Send pre-generated variations
        };

        const response = await causalExperimentApi.runExperiment(
          experimentData
        );
        experimentResult.value = response.data;
        showResultsModal.value = true;
      } catch (error) {
        console.error("Full error object:", error);
        console.error("Error response:", error.response);
        console.error("Error message:", error.message);

        let errorMessage = "Unknown error occurred";

        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        } else if (error.message) {
          errorMessage = error.message;
        }

        alert(`Error running causal experiment: ${errorMessage}`);
      } finally {
        isRunningExperiment.value = false;
      }
    };

    const downloadCausalReport = () => {
      if (!experimentResult.value) return;

      const content =
        experimentResult.value.causal_analysis ||
        "No causal analysis available";

      const blob = new Blob([content], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `causal-analysis-report-${Date.now()}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    const formatMarkdown = (text) => {
      if (!text) return "";

      // Convert markdown to HTML for display
      return text
        .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4">$1</h1>')
        .replace(
          /^## (.*$)/gim,
          '<h2 class="text-xl font-semibold mb-3 mt-6">$1</h2>'
        )
        .replace(
          /^### (.*$)/gim,
          '<h3 class="text-lg font-medium mb-2 mt-4">$1</h3>'
        )
        .replace(
          /^\*\*(.*)\*\*: (.*$)/gim,
          '<p class="mb-2"><strong class="font-semibold">$1:</strong> $2</p>'
        )
        .replace(/^• (.*$)/gim, '<li class="ml-4 mb-1">$1</li>')
        .replace(/^- (.*$)/gim, '<li class="ml-4 mb-1">$1</li>')
        .replace(/\n\n/g, '</p><p class="mb-4">')
        .replace(/\n/g, "<br>");
    };

    // Load saved experiments
    const loadSavedExperiments = async () => {
      try {
        const response = await causalExperimentApi.listExperiments();
        savedExperiments.value = response.data.experiments || [];
      } catch (error) {
        console.error("Error loading saved experiments:", error);
      }
    };

    // View saved experiment
    const viewSavedExperiment = async (experiment) => {
      try {
        const response = await causalExperimentApi.getExperiment(
          experiment.experiment_id
        );
        selectedSavedExperiment.value = response.data;
        showSavedExperimentModal.value = true;
      } catch (error) {
        console.error("Error loading experiment details:", error);
        alert(
          "Error loading experiment details: " +
            (error.response?.data?.detail || error.message)
        );
      }
    };

    // Download saved causal report
    const downloadSavedCausalReport = (experiment) => {
      if (!experiment.causal_analysis) {
        alert("No causal analysis report available for this experiment");
        return;
      }

      const blob = new Blob([experiment.causal_analysis], {
        type: "text/markdown",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `causal-analysis-${
        experiment.experiment_id
      }-${Date.now()}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    // Load saved experiments on component mount
    loadSavedExperiments();

    // Set up auto-refresh for saved experiments
    let refreshInterval = null;

    onMounted(() => {
      // Refresh saved experiments every 2 seconds
      refreshInterval = setInterval(() => {
        loadSavedExperiments();
      }, 1000);
    });

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    });

    // Reload saved experiments when component becomes active (tab switch)
    onActivated(() => {
      loadSavedExperiments();
    });

    return {
      selectedTestId,
      experimentDescription,
      numberOfTests,
      showResultsModal,
      experimentResult,
      generatedVariations,
      expandedVariations,
      allExpanded,
      isGeneratingVariations,
      isRunningExperiment,
      completedTests,
      failedTests,
      selectedTest,
      canRunExperiment,
      formatDateTime,
      getStatusClass,
      toggleVariation,
      toggleAllVariations,
      generateVariations,
      runCausalExperiment,
      downloadCausalReport,
      formatMarkdown,
      savedExperiments,
      showSavedExperimentModal,
      selectedSavedExperiment,
      viewSavedExperiment,
      downloadSavedCausalReport,
    };
  },
};
</script>
