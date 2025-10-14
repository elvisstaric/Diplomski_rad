<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <h1 class="text-xl font-semibold text-gray-900">
              Performance Testing Tool
            </h1>
          </div>
          <div class="flex items-center space-x-4">
            <div class="text-sm text-gray-500">
              Backend Status:
              <span
                :class="
                  backendStatus.available ? 'text-green-600' : 'text-red-600'
                "
              >
                {{ backendStatus.available ? "Connected" : "Disconnected" }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Tab Navigation -->
      <div class="mb-8">
        <nav class="flex space-x-8">
          <button
            @click="activeTab = 'test-config'"
            :class="[
              'py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200',
              activeTab === 'test-config'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ]"
          >
            Test Configuration
          </button>
          <button
            @click="activeTab = 'test-results'"
            :class="[
              'py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200',
              activeTab === 'test-results'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ]"
          >
            Test Results
          </button>
          <button
            @click="activeTab = 'causal-analysis'"
            :class="[
              'py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200',
              activeTab === 'causal-analysis'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            ]"
          >
            Causal Analysis
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="mt-6">
        <!-- Test Configuration Tab -->
        <TestConfiguration
          v-if="activeTab === 'test-config'"
          @test-started="handleTestStarted"
          @test-status-updated="handleTestStatusUpdated"
        />

        <!-- Test Results Tab -->
        <TestResults
          v-if="activeTab === 'test-results'"
          :tests="tests"
          :is-refreshing="isRefreshing"
          @refresh-tests="refreshTests"
        />

        <!-- Causal Analysis Tab -->
        <CausalAnalysis v-if="activeTab === 'causal-analysis'" :tests="tests" />
      </div>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import TestConfiguration from "./components/TestConfiguration.vue";
import TestResults from "./components/TestResults.vue";
import CausalAnalysis from "./components/CausalAnalysis.vue";
import { testApi } from "./services/api";

export default {
  name: "App",
  components: {
    TestConfiguration,
    TestResults,
    CausalAnalysis,
  },
  setup() {
    const activeTab = ref("test-config");
    const tests = ref([]);
    const backendStatus = ref({ available: false });
    const isRefreshing = ref(false);

    const checkBackendStatus = async () => {
      try {
        await testApi.pingBackend("http://localhost:8000");
        backendStatus.value = { available: true };
      } catch (error) {
        backendStatus.value = { available: false };
      }
    };

    const refreshTests = async () => {
      isRefreshing.value = true;
      try {
        const response = await testApi.listTests();
        const newTests = response.data;

        if (JSON.stringify(tests.value) !== JSON.stringify(newTests)) {
          tests.value = newTests;
        }
      } catch (error) {
        if (error.response?.status !== 404) {
          console.error("Error fetching tests:", error);
        }
      } finally {
        isRefreshing.value = false;
      }
    };

    const handleTestStarted = (testId) => {
      // Switch to results tab and refresh tests
      activeTab.value = "test-results";
      refreshTests();
    };

    const handleTestStatusUpdated = () => {
      refreshTests();
    };

    onMounted(() => {
      checkBackendStatus();
      setInterval(() => {
        if (backendStatus.value.available) {
          refreshTests();
        }
      }, 500);

      // Check backend status every 30 seconds
      setInterval(checkBackendStatus, 30000);
    });

    return {
      activeTab,
      tests,
      backendStatus,
      isRefreshing,
      refreshTests,
      handleTestStarted,
      handleTestStatusUpdated,
    };
  },
};
</script>
