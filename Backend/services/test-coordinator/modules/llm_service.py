import os
import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables. LLM functionality will be disabled.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    async def generate_dsl_from_description(self, description: str, swagger_docs: str = None, api_endpoints: List[str] = None, user_model: str = "closed", arrival_rate: float = None) -> Dict[str, Any]:
        if not self.client:
            return {
                "dsl_script": "",
                "status": "error",
                "error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            }
        
        try:
            system_prompt = self.get_system_prompt()
            api_info = ""
            if swagger_docs:
                api_info += f"\n\nSwagger documentation:\n{swagger_docs[:2000]}..." 
            if api_endpoints:
                api_info += f"\n\nAvailable API endpoints:\n" + "\n".join(api_endpoints)
            
            user_model_info = ""
            if user_model == "open":
                user_model_info = f"""
            User Model: Open Model
            - Use user_model: open
            - Set arrival_rate: {arrival_rate or 2.5} (users per second)
            - Set users: 0 (not relevant for open model)
            """
            else:
                user_model_info = f"""
            User Model: Closed Model
            - Use user_model: closed (or omit for default)
            - Set users: [appropriate number based on scenario]
            """
            
            user_prompt = f"""
            Generate a DSL script for the following user journey description:
            
            {description}
            
            {api_info}
            
            {user_model_info}
            
        Generate a complete DSL script that includes:
        1. Basic parameters (users, duration, pattern, user_model)
        2. User journey definitions with appropriate HTTP methods
        3. Realistic API endpoints and payloads (use available endpoints)
        4. Appropriate workload pattern for the described scenario
        5. User model configuration (open/closed with appropriate parameters)
        6. Resilience configuration (timeout and retry_attempts)
        
        IMPORTANT: Use the exact endpoint paths from the Swagger documentation. Do NOT add any prefixes like /api unless they are explicitly defined in the Swagger docs.
        
        Respond ONLY with the DSL script, without additional explanations.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            dsl_script = response.choices[0].message.content.strip()
            
            return {
                "dsl_script": dsl_script,
                "status": "success",
                "model_used": self.model
            }
            
        except Exception as e:
            logger.error(f"Error generating DSL from description: {e}")
            return {
                "dsl_script": "",
                "status": "error",
                "error": str(e)
            }
    
    async def optimize_existing_dsl(self, dsl_script: str, optimization_goal: str = "improve performance") -> Dict[str, Any]:
        if not self.client:
            return {
                "optimized_dsl": dsl_script,
                "explanation": "",
                "status": "error",
                "error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            }
        
        try:
            system_prompt = self.get_optimization_system_prompt()
            user_prompt = f"""
            Optimize the following DSL based on the SPECIFIC goal: {optimization_goal}
            
            Existing DSL:
            ```dsl
            {dsl_script}
            ```
            
            Your task:
            1. Analyze ONLY the specific optimization goal: {optimization_goal}
            2. Make MINIMAL changes - only modify what directly relates to this goal
            3. DO NOT add new variables, journeys, or parameters unless explicitly requested
            4. PRESERVE all existing values unless they directly conflict with the optimization goal
            5. Keep the same structure and format
            
            Respond with ONLY the optimized DSL and a brief explanation of the specific changes made for {optimization_goal}.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            
            if "```dsl" in result:
                parts = result.split("```dsl")
                if len(parts) > 1:
                    dsl_part = parts[1].split("```")[0].strip()
                    explanation = parts[0].strip() + (parts[1].split("```")[1] if "```" in parts[1] else "")
                else:
                    dsl_part = result
                    explanation = ""
            else:
                dsl_part = result
                explanation = ""
            
            return {
                "optimized_dsl": dsl_part,
                "explanation": explanation,
                "status": "success",
                "model_used": self.model
            }
            
        except Exception as e:
            logger.error(f"Error optimizing DSL: {e}")
            return {
                "optimized_dsl": dsl_script,
                "explanation": "",
                "status": "error",
                "error": str(e)
            }
    
    def get_system_prompt(self):
        return """
        You are an expert in generating DSL scripts for web application performance testing.
        
        Your task is to generate valid DSL scripts that:
        1. Define user journeys with realistic API calls
        2. Use appropriate HTTP methods (GET, POST, PUT, DELETE, PATCH)
        3. Include realistic payloads for POST/PUT requests
        4. Use suitable workload patterns (steady, burst, ramp_up, daily_cycle, spike, gradual_ramp)
        5. Define reasonable numbers of users and test duration
        6. Choose appropriate user model (closed or open)
        
        DSL format:
        - users: [number] - number of simulated users (0 for open model)
        - duration: [number] - duration in seconds
        - pattern: [pattern_name] - workload pattern
        - user_model: [closed|open] - user model type
        - arrival_rate: [number] - users per second (only for open model)
        - timeout: [number] - request timeout in seconds (default: 30)
        - retry_attempts: [number] - number of retry attempts for failed requests (default: 3)
        - journey: [name] - user journey name
        - repeat: [number] - number of repetitions (optional)
        - - [METHOD] [path] [payload] - step in journey
        - end - end of journey
        
        Examples:
        
        Closed Model:
        users: 10
        duration: 300
        pattern: steady
        user_model: closed
        timeout: 30
        retry_attempts: 3
        
        journey: ecommerce_flow
        repeat: 2
        - GET /products
        - POST /cart {"product_id": 123, "quantity": 1}
        - GET /cart
        - POST /checkout {"payment_method": "credit_card"}
        end
        
        journey: checkout_flow
        - GET /checkout
        - POST /checkout {"payment_method": "card"}
        - GET /confirmation
        end
        
        journey_percentages: ecommerce_flow:70,checkout_flow:30
        
        Open Model:
        users: 0
        duration: 300
        pattern: steady
        user_model: open
        arrival_rate: 2.5
        timeout: 30
        retry_attempts: 3
        
        journey: ecommerce_flow
        - GET /products
        - POST /cart {"product_id": 123, "quantity": 1}
        - GET /cart
        end
        
        journey: checkout_flow
        - GET /checkout
        - POST /checkout {"payment_method": "card"}
        - GET /confirmation
        end
        
        journey_percentages: ecommerce_flow:70,checkout_flow:30
        """
    
    def get_optimization_system_prompt(self):
        return """
        You are an expert in optimizing DSL scripts for performance testing.
        
        CRITICAL RULES:
        1. ONLY modify what is specifically requested in the optimization goal
        2. DO NOT add new variables or parameters unless explicitly requested
        3. DO NOT change user_model unless specifically asked
        4. DO NOT add new journeys unless specifically requested
        5. DO NOT modify existing journey steps unless optimization goal requires it
        6. PRESERVE all existing values unless optimization goal specifically targets them
        
        Your task is to analyze existing DSL and suggest improvements ONLY for the specific optimization goal provided.
        
        Available DSL parameters (use only if optimization goal requires changes):
        - users: [number] - number of simulated users (0 for open model)
        - duration: [number] - duration in seconds
        - pattern: [pattern_name] - workload pattern (steady, burst, ramp_up, daily_cycle, spike, gradual_ramp)
        - user_model: [closed|open] - user model type
        - arrival_rate: [number] - users per second (only for open model)
        - timeout: [number] - request timeout in seconds (default: 30)
        - retry_attempts: [number] - number of retry attempts for failed requests (default: 3)
        - auth_type: [none|basic|bearer|session] - authentication type
        - journey_percentages: [journey_name:percentage] - distribution of users across journeys
        
        IMPORTANT: 
        - Keep the same structure and format as the original DSL
        - Only change values that directly relate to the optimization goal
        - If optimization goal is about performance, focus on users, duration, pattern, timeout, retry_attempts
        - If optimization goal is about authentication, focus on auth_type and auth_credentials
        - If optimization goal is about user distribution, focus on journey_percentages
        - Do NOT add new parameters or journeys unless explicitly requested
        """
    
    async def generate_detailed_report(self, analysis_data: Dict[str, Any]):
        
        if not self.client:
            return "LLM service not available - cannot generate detailed report"
        
        try:
            system_prompt = self.get_report_system_prompt()
            user_prompt = self.format_analysis_data_for_report(analysis_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating detailed report: {e}")
            return f"Error generating report: {str(e)}"
    
    def get_report_system_prompt(self):
        return """
        You are an expert in web application performance analysis and generating detailed performance testing reports.
        
        Your task is to generate a professional report that includes:
        
        1. **Test Summary Report** - basic test statistics
        2. **Problem Detection** - detailed analysis of problems per endpoint with temporal context
        3. **Performance Insights** - insights into performance and causal relationships
        4. **Recommended Corrective Actions** - specific technical interventions
        
        Report structure:
        - Use clear headings and subheadings
        - Include specific numbers and percentages
        - Identify temporal patterns in errors
        - Explain possible causes of problems
        - Provide concrete, actionable recommendations
        
        Style:
        - Professional and technical
        - Clear and concise
        - Focused on actions that can improve performance
        - Use bullet points for easier reading
        """
    
    def format_analysis_data_for_report(self, analysis_data: Dict[str, Any]) -> str:
        """Format analysis data for LLM report generation"""
        test_summary = analysis_data.get("test_summary", {})
        endpoint_stats = analysis_data.get("endpoint_stats", {})
        error_patterns = analysis_data.get("error_patterns", [])
        performance_insights = analysis_data.get("performance_insights", [])
        recommendations = analysis_data.get("recommendations", [])
        
        formatted_data = f"""
        Analyze the following test data and generate a detailed report:
        
        **TEST SUMMARY:**
        - Test ID: {analysis_data.get('test_id', 'N/A')}
        - Test Duration: {test_summary.get('duration', 0)} seconds
        - Total Requests: {test_summary.get('total_requests', 0)}
        - Successful Requests: {test_summary.get('successful_requests', 0)} ({test_summary.get('success_rate', 0)}%)
        - Failed Requests: {test_summary.get('failed_requests', 0)} ({test_summary.get('failure_rate', 0)}%)
        - Average Latency: {test_summary.get('avg_latency', 0)}ms
        - Maximum Latency: {test_summary.get('max_latency', 0)}ms
        - Minimum Latency: {test_summary.get('min_latency', 0)}ms
        - Latency Variance: {test_summary.get('latency_variance', 0)}ms²
        - Requests per Second: {test_summary.get('requests_per_second', 0)}
        
        **ENDPOINT STATISTICS:**
        """
        
        for endpoint, stats in endpoint_stats.items():
            formatted_data += f"""
        - {endpoint}:
          o Total Requests: {stats.get('total_requests', 0)}
          o Success Rate: {stats.get('success_rate', 0)}%
          o Failure Rate: {stats.get('failure_rate', 0)}%
          o Critical Errors: {stats.get('critical_errors', 0)}
          o Most Common Error Type: {stats.get('most_common_error', ['N/A', 0])[0]} ({stats.get('most_common_error', ['N/A', 0])[1]} times)
          o Error Categories: {stats.get('error_categories', {})}
          o Error Severities: {stats.get('error_severities', {})}
        """
        
        formatted_data += f"""
        
        **ERROR PATTERN ANALYSIS:**
        """
        
        for pattern in error_patterns:
            formatted_data += f"""
        - {pattern.get('category', 'N/A')}:
          o Error Count: {pattern.get('count', 0)} ({pattern.get('percentage', 0)}% of total errors)
          o Endpoints: {', '.join(pattern.get('endpoints', []))}
          o Severity Distribution: {pattern.get('severity_distribution', {})}
          o Time Distribution: {pattern.get('time_distribution', {})}
          o Common Error Messages: {pattern.get('common_error_messages', [])}
        """
        
        formatted_data += f"""
        
        **PERFORMANCE INSIGHTS:**
        """
        for insight in performance_insights:
            formatted_data += f"• {insight}\n"
        
        formatted_data += f"""
        
        **RECOMMENDATIONS:**
        """
        for recommendation in recommendations:
            formatted_data += f"• {recommendation}\n"
        
        formatted_data += f"""
        
        Generate a detailed report following this structure:
        1. Test Summary Report with title
        2. Problem detection per endpoint with temporal context
        3. Performance insights with causal analysis
        4. Recommended corrective actions
        
        Use format similar to this example:
        "Test Summary Report – 'User Journey: [name]'
        Test Duration: [X] seconds
        Number of Concurrent Users: [X]
        Statistics: ...
        
        Problem Detection:
        1. [endpoint] endpoint
           o Errors: [X]% of requests returned [error type]
           o Temporal Context: [description of temporal patterns]
           o Request Pattern: [description of patterns]
           o Possible Cause: [cause analysis]
        
        Recommended Corrective Actions:
        • [specific recommendation]
        • [specific recommendation]
        
        Conclusion:
        [summary of findings and recommendations]"
        """
        
        return formatted_data
    
    async def generate_causal_experiment_variations(self, baseline_dsl: str, experiment_description: str, number_of_tests: int) -> Dict[str, Any]:
        """Generate DSL variations for causal experiment"""
        if not self.client:
            return {
                "variations": [],
                "status": "error",
                "error": "LLM service not available"
            }
        
        try:
            system_prompt = self.get_causal_experiment_system_prompt()
            user_prompt = f"""
            Generate {number_of_tests} DSL variations for causal experiment.
            
            Baseline DSL:
            ```dsl
            {baseline_dsl}
            ```
            
            Experiment Description: {experiment_description}
            
            CRITICAL INSTRUCTIONS:
            1. ONLY modify the specific parameter mentioned in the experiment description
            2. DO NOT change any other parameters (auth_type, timeout, retry_attempts, journey steps, etc.)
            3. If the experiment mentions "users" but the DSL has "user_model: open", DO NOT change arrival_rate
            4. If the experiment mentions "arrival rate" but the DSL has "user_model: closed", DO NOT change users
            5. PRESERVE all other parameters exactly as they are in the baseline DSL
            
            Generate variations that will help test the hypothesis described above.
            Each variation should be a complete DSL script.
            
            IMPORTANT: Return ONLY valid JSON array format. Do not include any markdown formatting or code blocks.
            
            Example format:
            [
                {{
                    "variation_name": "Control Group",
                    "dsl_script": "users: 10\\nduration: 10\\npattern: steady\\nuser_model: closed\\nauth_type: none\\ntimeout: 30\\nretry_attempts: 3\\njourney: test_flow\\n- GET /api/test",
                    "description": "Baseline with 10 users"
                }},
                {{
                    "variation_name": "Increased Load",
                    "dsl_script": "users: 15\\nduration: 10\\npattern: steady\\nuser_model: closed\\nauth_type: none\\ntimeout: 30\\nretry_attempts: 3\\njourney: test_flow\\n- GET /api/test",
                    "description": "Test with 15 users"
                }}
            ]
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
 
            try:
                import json
                variations = json.loads(result_text)
                return {
                    "variations": variations,
                    "status": "success",
                    "model_used": self.model
                }
            except json.JSONDecodeError as e:
                variations = self.extract_variations_from_text(result_text)
                return {
                    "variations": variations,
                    "status": "success",
                    "model_used": self.model
                }
            
        except Exception as e:
            logger.error(f"Error generating causal experiment variations: {e}")
            return {
                "variations": [],
                "status": "error",
                "error": str(e)
            }
    
    def get_causal_experiment_system_prompt(self):
        return """
        You are an expert in designing causal experiments for performance testing.
        
        CRITICAL RULES FOR DSL VARIATIONS:
        1. ONLY modify parameters that are EXPLICITLY mentioned in the experiment description
        2. DO NOT change unrelated parameters (e.g., if asked to change users, don't change arrival_rate)
        3. DO NOT change auth_type, timeout, retry_attempts unless specifically requested
        4. DO NOT change journey steps unless specifically requested
        5. DO NOT change user_model unless specifically requested
        6. DO NOT change pattern unless specifically requested
        
        PARAMETER MAPPING:
        - "users" parameter: ONLY for closed model (user_model: closed)
        - "arrival_rate" parameter: ONLY for open model (user_model: open)
        - If experiment mentions "users" but DSL has user_model: open, DO NOT change arrival_rate
        - If experiment mentions "arrival rate" but DSL has user_model: closed, DO NOT change users
        
        EXAMPLES:
        - If asked to "increase users by 5" and DSL has "user_model: closed", change "users: X" to "users: X+5"
        - If asked to "increase users by 5" and DSL has "user_model: open", DO NOT change arrival_rate
        - If asked to "change pattern to burst", only change "pattern: X" to "pattern: burst"
        - If asked to "increase duration", only change "duration: X" to "duration: Y"
        
        GUIDELINES:
        1. Create meaningful variations that test the hypothesis
        2. Include a control group (baseline)
        3. Vary ONLY the parameters relevant to the hypothesis
        4. Ensure variations are realistic and testable
        5. Each variation should be a complete, valid DSL script
        6. PRESERVE all other parameters exactly as they are in the baseline
        
        Always return valid JSON array format.
        """
    
    def extract_variations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract variations from LLM text response when JSON parsing fails"""
        variations = []
        lines = text.split('\n')
        
        current_variation = {}
        current_dsl = []
        in_dsl_block = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('"variation_name"'):
                if current_variation:
                    current_variation['dsl_script'] = '\n'.join(current_dsl)
                    variations.append(current_variation)
                current_variation = {}
                current_dsl = []
                in_dsl_block = False
                
                name = line.split(':', 1)[1].strip().strip('"')
                current_variation['variation_name'] = name
                
            elif line.startswith('"description"'):
                desc = line.split(':', 1)[1].strip().strip('"')
                current_variation['description'] = desc
                
            elif line.startswith('"dsl_script"'):
                in_dsl_block = True
                
            elif in_dsl_block and line and not line.startswith('"'):
                current_dsl.append(line)
        
        
        if current_variation:
            current_variation['dsl_script'] = '\n'.join(current_dsl)
            variations.append(current_variation)
        
        return variations
    
    async def generate_causal_report(self, causal_data: Dict[str, Any]):
        """Generate causal analysis report using LLM"""
        if not self.client:
            return {
                "report": "LLM service not available - cannot generate causal report",
                "status": "error",
                "error": "LLM service not available"
            }
        
        try:
            system_prompt = self.get_causal_report_system_prompt()
            user_prompt = self.format_causal_data_for_report(causal_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            report = response.choices[0].message.content.strip()
            
            return {
                "report": report,
                "status": "success",
                "model_used": self.model
            }
            
        except Exception as e:
            logger.error(f"Error generating causal report: {e}")
            return {
                "report": f"Error generating causal report: {str(e)}",
                "status": "error",
                "error": str(e)
            }
    
    def get_causal_report_system_prompt(self):
        return """
        You are an expert in causal analysis and generating detailed causal inference reports.
        
        Your task is to generate a professional causal analysis report that includes:
        
        1. **Experiment Overview** - description and hypothesis
        2. **Causal Analysis Results** - detailed analysis of causal effects
        3. **Refutation Tests** - robustness checks and validation
        4. **Data Summary** - sample size, treatment groups, observations
        6. **Endpoint-Specific Analysis** - per-endpoint causal effects
        7. **Recommendations** - actionable insights based on findings
        
        Report structure:
        - Use clear headings and subheadings
        - Include specific numbers and statistical measures
        - Explain causal relationships and their implications
        - Provide concrete, actionable recommendations
        - Use professional statistical terminology
        
        Style:
        - Professional and technical
        - Clear and concise
        - Focused on causal relationships and their practical implications
        - Use bullet points for easier reading
        - Include confidence levels and statistical significance
        
        IMPORTANT: Refutation Tests Interpretation:
        - In refutation tests, a p-value CLOSE TO 1.0 is GOOD and indicates robustness
        - P-value near 1.0 means the original causal effect is NOT due to random chance
        - P-value near 0.0 means the causal effect might be spurious or random
        - Always explain that high p-values (>0.8) in refutation tests validate the causal findings
        - Low p-values (<0.2) in refutation tests suggest the causal effect may not be reliable
        """
    
    def format_causal_data_for_report(self, causal_data: Dict[str, Any]) -> str:
        """Format causal analysis data for LLM report generation"""
        experiment_description = causal_data.get("experiment_description", "Causal Analysis")
        analysis_type = causal_data.get("analysis_type", "Causal Analysis")
    
        if causal_data.get("multi_metric", False):
            return self.format_multi_metric_causal_data(causal_data, experiment_description, analysis_type)
        
        causal_results = causal_data.get("causal_results", {})
        causal_estimate = causal_data.get("causal_estimate", {})
        refutation_test = causal_data.get("refutation_test", {})
        data_summary = causal_data.get("data_summary", {})
        endpoint_analyses = causal_data.get("endpoint_analyses", {})
        
        formatted_data = f"""
        Generate a detailed causal analysis report based on the following data:
        
        **EXPERIMENT DESCRIPTION:**
        {experiment_description}
        
        **ANALYSIS TYPE:**
        {analysis_type}
        
        **CAUSAL ESTIMATE:**
        {causal_estimate}
        
        **REFUTATION TEST:**
        {refutation_test}
        
        **DATA SUMMARY:**
        - Total Observations: {data_summary.get('total_observations', 0)}
        - Treatment Groups: {data_summary.get('treatment_groups', 0)}
        - Endpoints: {data_summary.get('endpoints', 0)}
        - Mean Outcome by Treatment: {data_summary.get('mean_outcome_by_treatment', {})}
        
        **ENDPOINT-SPECIFIC ANALYSES:**
        """
        
        for analysis_name, analysis_data in endpoint_analyses.items():
            if "error" in analysis_data:
                continue
                
            endpoint_name = analysis_name.split("_")[0]
            metric_type = analysis_name.split("_")[1]
            
            formatted_data += f"""
        - {endpoint_name} - {metric_type.title()}:
          o Causal Estimate: {analysis_data.get('causal_estimate', {})}
          o Refutation Test: {analysis_data.get('refutation_test', {})}
          o Data Summary: {analysis_data.get('data_summary', {})}
        """
        
        formatted_data += f"""
        
        Generate a detailed causal analysis report following this structure:
        1. Experiment Overview with hypothesis
        2. Causal Analysis Results with statistical measures
        3. Refutation Tests and robustness checks
        4. Data Summary and sample characteristics
        6. Endpoint-Specific Analysis
        7. Recommendations and actionable insights
        
        Use format similar to this example:
        "# Causal Analysis Report – '[experiment description]'
        
        ## Test Summary Report
        **Experiment Description:** [description]
        **Analysis Type:** [type]
        **Total Observations:** [number] observations
        **Treatment Groups:** [number] groups
        **Endpoints Analyzed:** [number] endpoints
        
        ## Causal Analysis Results
        **Causal Effect:** [value with confidence interval]
        **Method Used:** [estimation method]
        
        ## Refutation Tests
        **Robustness Check:** [refutation test results with p-value interpretation]
        **Validation Method:** [refutation method used]
        **Interpretation:** [Explain that p-value close to 1.0 indicates robust causal effect, while p-value close to 0.0 suggests spurious results]
        
        ## Data Summary
        **Sample Size:** [number] observations
        **Treatment Groups:** [number] groups
        **Mean Outcomes by Treatment:** [detailed breakdown]
        
        ## Endpoint-Specific Analysis
        ### [Endpoint] - [Metric]
        **Causal Effect:** [value]
        **Confidence Interval:** [range]
        
        ## Performance Insights
        • [insight about causal relationships]
        • [insight about treatment effects]
        • [insight about data quality]
        
        ## Recommended Corrective Actions
        • [specific recommendation based on findings]
        • [specific recommendation based on findings]
        • [specific recommendation based on findings]
        
        ## Conclusion
        [summary of findings and implications for performance optimization]"
        """
        
        return formatted_data
    
    def format_multi_metric_causal_data(self, causal_data: Dict[str, Any], experiment_description: str, analysis_type: str) -> str:
        """Format multi-metric causal analysis data for LLM report generation"""
        latency_analysis = causal_data.get("latency_analysis", {})
        success_rate_analysis = causal_data.get("success_rate_analysis", {})
        error_rate_analysis = causal_data.get("error_rate_analysis", {})
        
        formatted_data = f"""
        Generate a comprehensive multi-metric causal analysis report based on the following data:
        
        **EXPERIMENT DESCRIPTION:**
        {experiment_description}
        
        **ANALYSIS TYPE:**
        {analysis_type}
        
        **LATENCY ANALYSIS:**
        """
        
        if latency_analysis and "error" not in latency_analysis:
            formatted_data += f"""
        - Causal Estimate: {latency_analysis.get("causal_estimate", {})}
        - Refutation Test: {latency_analysis.get("refutation_test", {})}
        - Data Summary: {latency_analysis.get("data_summary", {})}
        - Analysis Type: {latency_analysis.get("analysis_type", "Latency Analysis")}
        """
        else:
            formatted_data += f"""
        - Error: {latency_analysis.get("error", "No latency analysis available")}
        """
        
        formatted_data += f"""
        
        **SUCCESS RATE ANALYSIS:**
        """
        
        if success_rate_analysis and "error" not in success_rate_analysis:
            formatted_data += f"""
        - Causal Estimate: {success_rate_analysis.get("causal_estimate", {})}
        - Refutation Test: {success_rate_analysis.get("refutation_test", {})}
        - Data Summary: {success_rate_analysis.get("data_summary", {})}
        - Analysis Type: {success_rate_analysis.get("analysis_type", "Success Rate Analysis")}
        """
        else:
            formatted_data += f"""
        - Error: {success_rate_analysis.get("error", "No success rate analysis available")}
        """
        
        formatted_data += f"""
        
        **ERROR RATE ANALYSIS:**
        """
        
        if error_rate_analysis and "error" not in error_rate_analysis:
            # Check if there's a note about no variation
            if "note" in error_rate_analysis:
                formatted_data += f"""
        - Note: {error_rate_analysis.get("note", "")}
        - Data Summary: {error_rate_analysis.get("data_summary", {})}
        - Analysis Type: {error_rate_analysis.get("analysis_type", "Error Rate Analysis")}
        """
            else:
                formatted_data += f"""
        - Causal Estimate: {error_rate_analysis.get("causal_estimate", {})}
        - Refutation Test: {error_rate_analysis.get("refutation_test", {})}
        - Data Summary: {error_rate_analysis.get("data_summary", {})}
        - Analysis Type: {error_rate_analysis.get("analysis_type", "Error Rate Analysis")}
        """
        else:
            formatted_data += f"""
        - Error: {error_rate_analysis.get("error", "No error rate analysis available")}
        """
        
        formatted_data += f"""
        
        Generate a comprehensive multi-metric causal analysis report following this structure:
        1. Experiment Overview with hypothesis
        2. Multi-Metric Causal Analysis Results (Latency, Success Rate, Error Rate)
        3. Refutation Tests and robustness checks for each metric
        4. Comparative Analysis across metrics
        5. Data Summary and sample characteristics
        7. Endpoint-Specific Analysis (if available)
        8. Recommendations and actionable insights based on all metrics
        
        Use format similar to this example:
        "# Multi-Metric Causal Analysis Report – '[experiment description]'
        
        ## Test Summary Report
        **Experiment Description:** [description]
        **Analysis Type:** Multi-Metric Causal Analysis
        **Metrics Analyzed:** Latency, Success Rate, Error Rate
        
        ## Multi-Metric Causal Analysis Results
        
        ### Latency Analysis
        **Causal Effect on Latency:** [value with confidence interval]
        **Method Used:** [estimation method]
        
        ### Success Rate Analysis
        **Causal Effect on Success Rate:** [value with confidence interval]
        **Method Used:** [estimation method]
        
        ### Error Rate Analysis
        **Causal Effect on Error Rate:** [value with confidence interval OR note about no variation]
        **Method Used:** [estimation method OR "Not applicable - no error variation"]
        
        ## Refutation Tests
        **Latency Robustness Check:** [refutation test results with p-value interpretation]
        **Success Rate Robustness Check:** [refutation test results with p-value interpretation]
        **Error Rate Robustness Check:** [refutation test results with p-value interpretation OR "Not applicable - no error variation"]
        **Overall Interpretation:** [Explain that p-values close to 1.0 across all metrics indicate robust causal effects]
        
        ## Comparative Analysis
        **Metric Correlation:** [analysis of relationships between metrics]
        **Treatment Impact Ranking:** [ranking of treatment effects across metrics]
        **Consistency Check:** [analysis of consistency across metrics]
        
        ## Data Summary
        **Sample Size:** [number] observations
        **Treatment Groups:** [number] groups
        **Mean Outcomes by Treatment:** [detailed breakdown for each metric]
        
        ## Performance Insights
        • [insight about latency causal relationships]
        • [insight about success rate causal relationships]
        • [insight about error rate causal relationships]
        • [insight about cross-metric relationships]
        
        ## Recommended Corrective Actions
        • [specific recommendation based on latency findings]
        • [specific recommendation based on success rate findings]
        • [specific recommendation based on error rate findings]
        • [specific recommendation based on multi-metric analysis]
        
        ## Conclusion
        [comprehensive summary of findings across all metrics and implications for performance optimization]"
        """
        
        return formatted_data
    

llm_service = LLMService()
