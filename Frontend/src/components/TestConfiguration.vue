<template>
  <div class="space-y-6">
    <!-- Test Configuration Form -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">
        Test Configuration
      </h2>

      <form @submit.prevent="handleSubmit" class="space-y-6">
        <!-- Target URL -->
        <div>
          <label class="form-label">Target URL</label>
          <input
            v-model="formData.targetUrl"
            type="url"
            class="form-input"
            placeholder="https://api.example.com"
            required
          />
        </div>

        <!-- DSL Generation Method -->
        <div>
          <label class="form-label">DSL Generation Method</label>
          <div class="space-y-3">
            <label class="flex items-center">
              <input
                v-model="formData.dslMethod"
                type="radio"
                value="manual"
                class="mr-3"
              />
              <span>Manual DSL Definition</span>
            </label>
            <label class="flex items-center">
              <input
                v-model="formData.dslMethod"
                type="radio"
                value="llm"
                class="mr-3"
              />
              <span>Generate with LLM</span>
            </label>
          </div>
        </div>

        <!-- LLM Configuration (shown when LLM is selected) -->
        <div
          v-if="formData.dslMethod === 'llm'"
          class="space-y-4 p-4 bg-blue-50 rounded-lg"
        >
          <h3 class="font-medium text-gray-900">LLM Configuration</h3>

          <!-- Description -->
          <div>
            <label class="form-label">Test Description</label>
            <textarea
              v-model="formData.description"
              class="form-input"
              rows="3"
              placeholder="Describe the user journey you want to test..."
            ></textarea>
          </div>

          <!-- Swagger Documentation -->
          <div>
            <label class="form-label">Swagger Documentation (Optional)</label>
            <textarea
              v-model="formData.swaggerDocs"
              class="form-input"
              rows="4"
              placeholder="Paste your Swagger/OpenAPI documentation here..."
            ></textarea>
          </div>

          <!-- API Endpoints -->
          <div>
            <label class="form-label">API Endpoints (Optional)</label>
            <div class="space-y-2">
              <div
                v-for="(endpoint, index) in formData.apiEndpoints"
                :key="index"
                class="flex space-x-2"
              >
                <input
                  v-model="formData.apiEndpoints[index]"
                  type="text"
                  class="form-input flex-1"
                  placeholder="GET /api/users"
                />
                <button
                  type="button"
                  @click="removeEndpoint(index)"
                  class="btn-secondary text-red-600 hover:bg-red-50"
                >
                  Remove
                </button>
              </div>
              <button
                type="button"
                @click="addEndpoint"
                class="btn-secondary text-sm"
              >
                + Add Endpoint
              </button>
            </div>
          </div>

          <!-- Review DSL Option -->
          <div>
            <label class="flex items-center">
              <input
                v-model="formData.reviewDsl"
                type="checkbox"
                class="mr-3"
              />
              <span>Review and edit generated DSL before running test</span>
            </label>
          </div>
        </div>

        <!-- Manual DSL (shown when manual is selected) -->
        <div v-if="formData.dslMethod === 'manual'">
          <label class="form-label">DSL Script</label>
          <textarea
            v-model="formData.dslScript"
            class="form-input font-mono text-sm"
            rows="15"
            placeholder="users: 10&#10;duration: 300&#10;pattern: steady&#10;&#10;journey: test_flow&#10;- GET /api/test&#10;end"
          ></textarea>

          <!-- Optimization Instructions -->
          <div class="mt-4">
            <label class="form-label"
              >Optimization Instructions (Optional)</label
            >
            <textarea
              v-model="formData.optimizationInstructions"
              class="form-input"
              rows="3"
              placeholder="e.g., Increase user count, add more realistic delays, optimize request patterns..."
            ></textarea>
            <p class="text-sm text-gray-500 mt-1">
              Provide specific instructions on how you want the DSL to be
              optimized
            </p>
          </div>
        </div>

        <!-- Auth Credentials -->
        <div>
          <label class="form-label"
            >Authentication Credentials (Optional)</label
          >
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="text-sm text-gray-600">Username</label>
              <input
                v-model="formData.authCredentials.username"
                type="text"
                class="form-input"
                placeholder="username"
              />
            </div>
            <div>
              <label class="text-sm text-gray-600">Password</label>
              <input
                v-model="formData.authCredentials.password"
                type="password"
                class="form-input"
                placeholder="password"
              />
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex space-x-4">
          <button
            type="submit"
            :disabled="isLoading"
            class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isLoading">Starting Test...</span>
            <span v-else>Start Test</span>
          </button>

          <button
            v-if="formData.dslMethod === 'manual'"
            type="button"
            @click="validateDsl"
            :disabled="isValidating"
            class="btn-secondary disabled:opacity-50"
          >
            <span v-if="isValidating">Validating...</span>
            <span v-else>Validate DSL</span>
          </button>

          <button
            v-if="formData.dslMethod === 'manual'"
            type="button"
            @click="optimizeDsl"
            :disabled="isOptimizing"
            class="btn-secondary disabled:opacity-50"
          >
            <span v-if="isOptimizing">Optimizing...</span>
            <span v-else>Optimize DSL</span>
          </button>
        </div>
      </form>
    </div>

    <!-- DSL Preview Modal -->
    <div
      v-if="showDslPreview"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden"
      >
        <div
          class="flex justify-between items-center p-4 border-b border-gray-200"
        >
          <h3 class="text-lg font-semibold">Generated DSL Preview</h3>
          <button
            @click="showDslPreview = false"
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

        <div class="p-4 overflow-y-auto max-h-96">
          <pre
            class="bg-gray-100 p-4 rounded-lg text-sm font-mono whitespace-pre-wrap"
            >{{ generatedDsl }}</pre
          >
        </div>

        <div class="flex justify-end space-x-3 p-4 border-t border-gray-200">
          <button @click="showDslPreview = false" class="btn-secondary">
            Cancel
          </button>
          <button @click="editDsl" class="btn-primary">Edit DSL</button>
          <button @click="runTestWithDsl" class="btn-primary">Run Test</button>
        </div>
      </div>
    </div>

    <!-- DSL Editor Modal -->
    <div
      v-if="showDslEditor"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden"
      >
        <div
          class="flex justify-between items-center p-4 border-b border-gray-200"
        >
          <h3 class="text-lg font-semibold">Edit DSL</h3>
          <button
            @click="showDslEditor = false"
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

        <div class="p-4">
          <textarea
            v-model="editableDsl"
            class="form-input font-mono text-sm w-full h-96"
            placeholder="Edit your DSL script here..."
          ></textarea>
        </div>

        <div class="flex justify-end space-x-3 p-4 border-t border-gray-200">
          <button @click="showDslEditor = false" class="btn-secondary">
            Cancel
          </button>
          <button @click="saveEditedDsl" class="btn-primary">
            Save & Run Test
          </button>
        </div>
      </div>
    </div>

    <!-- Optimized DSL Modal -->
    <div
      v-if="showOptimizedDsl"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden"
      >
        <div
          class="flex justify-between items-center p-4 border-b border-gray-200"
        >
          <h3 class="text-lg font-semibold">Optimized DSL</h3>
          <button
            @click="showOptimizedDsl = false"
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

        <div class="p-4 overflow-y-auto max-h-96">
          <!-- Optimization Instructions -->
          <div v-if="formData.optimizationInstructions" class="mb-4">
            <h4 class="text-sm font-medium text-gray-700 mb-2">
              Optimization Instructions:
            </h4>
            <div class="bg-blue-50 p-3 rounded-lg border border-blue-200">
              <p class="text-sm text-blue-800">
                {{ formData.optimizationInstructions }}
              </p>
            </div>
          </div>

          <!-- Optimization Explanation -->
          <div v-if="optimizationExplanation" class="mb-4">
            <h4 class="text-sm font-medium text-gray-700 mb-2">
              Optimization Changes:
            </h4>
            <div class="bg-yellow-50 p-3 rounded-lg border border-yellow-200">
              <p class="text-sm text-yellow-800">
                {{ optimizationExplanation }}
              </p>
            </div>
          </div>

          <!-- Original DSL -->
          <div class="mb-4">
            <h4 class="text-sm font-medium text-gray-700 mb-2">
              Original DSL:
            </h4>
            <pre
              class="bg-gray-100 p-3 rounded-lg text-sm font-mono whitespace-pre-wrap text-gray-600"
              >{{ formData.dslScript }}</pre
            >
          </div>

          <!-- Optimized DSL -->
          <div>
            <h4 class="text-sm font-medium text-gray-700 mb-2">
              Optimized DSL:
            </h4>
            <pre
              class="bg-green-50 p-3 rounded-lg text-sm font-mono whitespace-pre-wrap border border-green-200"
              >{{ optimizedDsl }}</pre
            >
          </div>
        </div>

        <div class="flex justify-end space-x-3 p-4 border-t border-gray-200">
          <button @click="showOptimizedDsl = false" class="btn-secondary">
            Cancel
          </button>
          <button @click="useOptimizedDsl" class="btn-primary">
            Use Optimized DSL
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from "vue";
import { testApi, dslApi } from "../services/api";

export default {
  name: "TestConfiguration",
  emits: ["test-started", "test-status-updated"],
  setup(props, { emit }) {
    const isLoading = ref(false);
    const isValidating = ref(false);
    const isOptimizing = ref(false);
    const showDslPreview = ref(false);
    const showDslEditor = ref(false);
    const showOptimizedDsl = ref(false);
    const generatedDsl = ref("");
    const editableDsl = ref("");
    const optimizedDsl = ref("");
    const optimizationExplanation = ref("");

    const formData = reactive({
      targetUrl: "",
      dslMethod: "manual",
      description: "",
      swaggerDocs: "",
      apiEndpoints: [""],
      reviewDsl: true,
      dslScript: `users: 10
duration: 300
pattern: steady

journey: test_flow
- GET /api/test
end`,
      optimizationInstructions: "",
      authCredentials: {
        username: "",
        password: "",
      },
    });

    const addEndpoint = () => {
      formData.apiEndpoints.push("");
    };

    const removeEndpoint = (index) => {
      formData.apiEndpoints.splice(index, 1);
    };

    const validatePattern = (dslScript) => {
      const validPatterns = [
        "burst",
        "steady",
        "ramp_up",
        "daily_cycle",
        "spike",
        "gradual_ramp",
      ];
      const lines = dslScript.split("\n");

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith("pattern:")) {
          const patternValue = trimmedLine.split(":")[1].trim();
          if (!validPatterns.includes(patternValue)) {
            return {
              isValid: false,
              message: `Invalid pattern '${patternValue}'. Valid patterns are: ${validPatterns.join(
                ", "
              )}`,
            };
          }
        }
      }

      return { isValid: true };
    };

    const validateDsl = async () => {
      if (!formData.dslScript.trim()) {
        alert("Please enter a DSL script to validate");
        return;
      }

      // First check pattern locally
      const patternCheck = validatePattern(formData.dslScript);
      if (!patternCheck.isValid) {
        alert(`Pattern validation failed:\n${patternCheck.message}`);
        return;
      }

      isValidating.value = true;
      try {
        const response = await dslApi.validateDsl(formData.dslScript);
        const result = response.data;

        if (result.valid) {
          alert("DSL is valid!");
        } else {
          alert(`DSL validation failed:\n${result.issues.join("\n")}`);
        }
      } catch (error) {
        console.error("Validation error:", error);
        alert(
          "Error validating DSL: " +
            (error.response?.data?.detail || error.message)
        );
      } finally {
        isValidating.value = false;
      }
    };

    const optimizeDsl = async () => {
      if (!formData.dslScript.trim()) {
        alert("Please enter a DSL script to optimize");
        return;
      }

      isOptimizing.value = true;
      try {
        const requestData = {
          dsl_script: formData.dslScript,
          optimization_goal:
            formData.optimizationInstructions || "improve performance",
        };

        const response = await dslApi.optimizeDsl(requestData);
        const result = response.data;

        if (result.status === "success") {
          optimizedDsl.value = result.dsl_script;
          optimizationExplanation.value = result.explanation || "";
          showOptimizedDsl.value = true;
        } else {
          throw new Error(result.error || "Failed to optimize DSL");
        }
      } catch (error) {
        console.error("DSL optimization error:", error);
        alert("Error optimizing DSL");
      } finally {
        isOptimizing.value = false;
      }
    };

    const generateDsl = async () => {
      try {
        const requestData = {
          description: formData.description,
          swagger_docs: formData.swaggerDocs || null,
          api_endpoints: formData.apiEndpoints.filter((ep) => ep.trim()),
          target_url: formData.targetUrl,
          auto_run: false,
        };

        const response = await dslApi.generateDsl(requestData);
        const result = response.data;

        if (result.status === "success") {
          generatedDsl.value = result.dsl_script;
          return result.dsl_script;
        } else {
          throw new Error(result.error || "Failed to generate DSL");
        }
      } catch (error) {
        console.error("DSL generation error");
        throw error;
      }
    };

    const editDsl = () => {
      editableDsl.value = generatedDsl.value;
      showDslPreview.value = false;
      showDslEditor.value = true;
    };

    const saveEditedDsl = () => {
      formData.dslScript = editableDsl.value;
      showDslEditor.value = false;
      runTest();
    };

    const useOptimizedDsl = () => {
      formData.dslScript = optimizedDsl.value;
      showOptimizedDsl.value = false;
    };

    const runTestWithDsl = () => {
      formData.dslScript = generatedDsl.value;
      showDslPreview.value = false;
      runTest();
    };

    const runTest = async () => {
      const patternCheck = validatePattern(formData.dslScript);
      if (!patternCheck.isValid) {
        alert(`Cannot start test:\n${patternCheck.message}`);
        return;
      }

      isLoading.value = true;
      try {
        const testId = `test_${Date.now()}`;
        const testData = {
          test_id: testId,
          target_url: formData.targetUrl,
          dsl_script: formData.dslScript,
          swagger_docs: formData.swaggerDocs || null,
          auth_credentials: formData.authCredentials,
        };

        const response = await testApi.createTest(testData);

        if (response.data.status === "created") {
          emit("test-started", testId);
          alert("Test started successfully!");
        } else {
          throw new Error("Failed to start test");
        }
      } catch (error) {
        console.error("Test creation error:", error);
        alert("Error starting test");
      } finally {
        isLoading.value = false;
      }
    };

    const handleSubmit = async () => {
      if (formData.dslMethod === "llm") {
        try {
          const dsl = await generateDsl();

          if (formData.reviewDsl) {
            generatedDsl.value = dsl;
            showDslPreview.value = true;
          } else {
            formData.dslScript = dsl;
            await runTest();
          }
        } catch (error) {
          alert("Error generating DSL");
        }
      } else {
        await runTest();
      }
    };

    return {
      formData,
      isLoading,
      isValidating,
      isOptimizing,
      showDslPreview,
      showDslEditor,
      showOptimizedDsl,
      generatedDsl,
      editableDsl,
      optimizedDsl,
      optimizationExplanation,
      addEndpoint,
      removeEndpoint,
      validateDsl,
      optimizeDsl,
      editDsl,
      saveEditedDsl,
      useOptimizedDsl,
      runTestWithDsl,
      handleSubmit,
    };
  },
};
</script>
