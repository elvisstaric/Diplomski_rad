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
    
    async def generate_dsl_from_description(self, description: str, swagger_docs: str = None, api_endpoints: List[str] = None, user_model: str = "closed", arrival_rate: float = None, session_duration: float = None) -> Dict[str, Any]:
        if not self.client:
            return {
                "dsl_script": "",
                "status": "error",
                "error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            }
        
        try:
            system_prompt = self._get_system_prompt()
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
            - Set session_duration: {session_duration or 45} (average session duration in seconds)
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
            system_prompt = self._get_optimization_system_prompt()
            user_prompt = f"""
            Optimize the following DSL based on the goal: {optimization_goal}
            
            Existing DSL:
            ```dsl
            {dsl_script}
            ```
            
            Your task:
            1. Analyze the existing DSL
            2. Suggest improvements for {optimization_goal}
            3. Generate an optimized version
            4. Explain key changes
            
            Respond with the optimized DSL and a brief explanation of changes.
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
    
    def _get_system_prompt(self):
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
        - session_duration: [number] - average session duration in seconds (only for open model)
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
        - GET /api/products
        - POST /api/cart {"product_id": 123, "quantity": 1}
        - GET /api/cart
        - POST /api/checkout {"payment_method": "credit_card"}
        end
        
        Open Model:
        users: 0
        duration: 300
        pattern: steady
        user_model: open
        arrival_rate: 2.5
        session_duration: 45
        timeout: 30
        retry_attempts: 3
        
        journey: ecommerce_flow
        - GET /api/products
        - POST /api/cart {"product_id": 123, "quantity": 1}
        - GET /api/cart
        - POST /api/checkout {"payment_method": "credit_card"}
        end
        """
    
    def _get_optimization_system_prompt(self):
        return """
        You are an expert in optimizing DSL scripts for performance testing.
        
        Your task is to analyze existing DSL and suggest improvements for:
        - Increasing test performance
        - More realistic user journeys
        - Better workload patterns
        - Optimizing number of users and duration
        - Adding validation steps
        - Choosing appropriate user model (closed vs open)
        - Optimizing arrival rates and session durations for open model
        
        Available DSL parameters:
        - users: [number] - number of simulated users (0 for open model)
        - duration: [number] - duration in seconds
        - pattern: [pattern_name] - workload pattern (steady, burst, ramp_up, daily_cycle, spike, gradual_ramp)
        - user_model: [closed|open] - user model type
        - arrival_rate: [number] - users per second (only for open model)
        - session_duration: [number] - average session duration in seconds (only for open model)
        - timeout: [number] - request timeout in seconds (default: 30)
        - retry_attempts: [number] - number of retry attempts for failed requests (default: 3)
        
        Always maintain the basic DSL structure and add only meaningful improvements.
        Consider switching between closed and open models based on the optimization goal.
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
        - Average Latency: {test_summary.get('avg_latency', 0)}s
        - Maximum Latency: {test_summary.get('max_latency', 0)}s
        - Minimum Latency: {test_summary.get('min_latency', 0)}s
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

llm_service = LLMService()
