import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dowhy import CausalModel
import logging

logger = logging.getLogger(__name__)

class CausalAnalysisEngine:
    """Engine for performing causal inference analysis using DoWhy library"""
    
    def __init__(self):
        self.logger = logger
        print("🔧 CausalAnalysisEngine initialized!")
    
    def create_experiment_dataframe(self, test_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create pandas DataFrame from test results for causal analysis"""
        try:
            # Debug: Print input test_results
            print(f"\n=== INPUT TEST_RESULTS DEBUG ===")
            print(f"Number of test results: {len(test_results)}")
            for i, result in enumerate(test_results):
                print(f"Test {i}: {result.get('test_id', 'NO_ID')} - {result.get('variation_name', 'NO_NAME')}")
                print(f"  Keys: {list(result.keys())}")
                print(f"  Status: {result.get('status', 'NO_STATUS')}")
                print(f"  Results: {result.get('results', {})}")
            print(f"=== END INPUT DEBUG ===\n")
            
            data_rows = []
            
            for i, result in enumerate(test_results):
                # Extract basic metrics
                variation_name = result.get("variation_name", f"variation_{i}")
                total_requests = result.get("total_requests", 0)
                success_rate = result.get("success_rate", 0)
                avg_latency = result.get("avg_latency", 0)
                failure_rate = result.get("failure_rate", 0)
                
                # Determine treatment level based on variation
                treatment_level = self.extract_treatment_level(variation_name, result)
                
                # Extract endpoint-specific data if available
                results_data = result.get("results", {})
                endpoint_stats = results_data.get("endpoint_stats", {})
                
                # Create rows for each endpoint
                if endpoint_stats:
                    for endpoint, stats in endpoint_stats.items():
                        endpoint_latency = stats.get("avg_latency", avg_latency)
                        endpoint_success_rate = stats.get("success_rate", success_rate)
                        endpoint_error_rate = stats.get("error_rate", failure_rate)
                        
                        data_rows.append({
                            "variation_name": variation_name,
                            "treatment": treatment_level,
                            "endpoint": endpoint,
                            "latency": endpoint_latency,
                            "success_rate": endpoint_success_rate,
                            "error_rate": endpoint_error_rate,
                            "total_requests": total_requests,
                            "timestamp": i * 30,  # Simulate time progression
                            "test_id": result.get("test_id", f"test_{i}")
                        })
                else:
                    # If no endpoint-specific data, create general row
                    data_rows.append({
                        "variation_name": variation_name,
                        "treatment": treatment_level,
                        "endpoint": "general",
                        "latency": avg_latency,
                        "success_rate": success_rate,
                        "error_rate": failure_rate,
                        "total_requests": total_requests,
                        "timestamp": i * 30,
                        "test_id": result.get("test_id", f"test_{i}")
                    })
            
            df = pd.DataFrame(data_rows)
            self.logger.info(f"Created DataFrame with {len(df)} rows from {len(test_results)} test results")
            
            # Debug: Print DataFrame info to console
            print(f"\n=== DATAFRAME DEBUG INFO ===")
            print(f"DataFrame shape: {df.shape}")
            print(f"DataFrame columns: {list(df.columns)}")
            if not df.empty:
                print(f"Treatment groups: {df['treatment'].value_counts().to_dict()}")
                print(f"Endpoints: {df['endpoint'].value_counts().to_dict()}")
                print(f"Sample data:")
                print(df.head())
                print(f"Data types:")
                print(df.dtypes)
            else:
                print("DataFrame is EMPTY!")
            print(f"=== END DATAFRAME DEBUG ===\n")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error creating experiment DataFrame: {e}")
            raise
    
    def extract_treatment_level(self, variation_name: str, result: Dict[str, Any]) -> int:
        """Extract treatment level from variation name and result data"""
        variation_lower = variation_name.lower()
        
        # Simple test: baseline = 0, everything else = 1
        if "baseline" in variation_lower or "control" in variation_lower:
            return 0
        else:
            return 1
    
    def analyze_causal_effect(self, df: pd.DataFrame, analysis_type: str = "latency") -> Dict[str, Any]:
        """Perform causal analysis using DoWhy"""
        try:
            # Debug: Print DataFrame info before analysis
            print(f"\n=== CAUSAL ANALYSIS DEBUG ===")
            print(f"Analysis type: {analysis_type}")
            print(f"DataFrame shape: {df.shape}")
            if not df.empty:
                print(f"Treatment groups: {df['treatment'].value_counts().to_dict()}")
                print(f"Outcome column ({analysis_type}): {df[analysis_type].describe()}")
            print(f"=== END CAUSAL ANALYSIS DEBUG ===\n")
            
            if df.empty:
                return {"error": "No data available for causal analysis"}
            
            # Prepare data based on analysis type
            if analysis_type == "latency":
                outcome_col = "latency"
                analysis_name = "Latency Analysis"
            elif analysis_type == "success_rate":
                outcome_col = "success_rate"
                analysis_name = "Success Rate Analysis"
            elif analysis_type == "error_rate":
                outcome_col = "error_rate"
                analysis_name = "Error Rate Analysis"
            else:
                outcome_col = "latency"
                analysis_name = "Latency Analysis"
            
            # Create causal model
            model = CausalModel(
                data=df,
                treatment="treatment",
                outcome=outcome_col,
                common_causes=[]  # No confounders for now
            )
            
            # Identify causal effect
            identified_estimand = model.identify_effect()
            logger.info(f"Identified estimand: {identified_estimand}")
            # Estimate causal effect
            estimate = model.estimate_effect(
                identified_estimand, 
                method_name="backdoor.linear_regression"
            )
            logger.info(f"Estimated effect: {estimate}")
            # Refute the estimate
            refute = model.refute_estimate(
                identified_estimand, 
                estimate, 
                method_name="placebo_treatment_refuter"
            )
            logger.info(f"Tu ti je Estimated effect: {estimate}")
            logger.info(f"Tu ti je refuted estimate: {refute}")
            
            # Extract results - use full objects instead of specific attributes
            causal_results = {
                "analysis_type": analysis_name,
                "treatment_variable": "treatment",
                "outcome_variable": outcome_col,
                "causal_estimate": self.serialize_dowhy_object(estimate),  # Convert to serializable format
                "refutation_test": self.serialize_dowhy_object(refute),      # Convert to serializable format
                "data_summary": {
                    "total_observations": len(df),
                    "treatment_groups": df["treatment"].nunique(),
                    "endpoints": df["endpoint"].nunique(),
                    "mean_outcome_by_treatment": df.groupby("treatment")[outcome_col].mean().to_dict()
                }
            }
            
            self.logger.info(f"Causal analysis completed for {analysis_name}")
            return causal_results
            
        except Exception as e:
            self.logger.error(f"Error in causal analysis: {e}")
            return {"error": f"Causal analysis failed: {str(e)}"}
    
    def analyze_multiple_endpoints(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze causal effects for multiple endpoints separately"""
        try:
            endpoint_analyses = {}
            endpoints = df["endpoint"].unique()
            
            for endpoint in endpoints:
                if endpoint == "general":
                    continue
                    
                endpoint_df = df[df["endpoint"] == endpoint]
                
                if len(endpoint_df) < 2:
                    continue
                
                # Analyze latency for this endpoint
                latency_analysis = self.analyze_causal_effect(endpoint_df, "latency")
                endpoint_analyses[f"{endpoint}_latency"] = latency_analysis
                
                # Analyze success rate for this endpoint
                success_analysis = self.analyze_causal_effect(endpoint_df, "success_rate")
                endpoint_analyses[f"{endpoint}_success"] = success_analysis
            
            return {
                "endpoint_analyses": endpoint_analyses,
                "summary": {
                    "total_endpoints": len(endpoints),
                    "analyzed_endpoints": len(endpoint_analyses) // 2  # Each endpoint has 2 analyses
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in multi-endpoint analysis: {e}")
            return {"error": f"Multi-endpoint analysis failed: {str(e)}"}
    
    async def generate_causal_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Generate human-readable causal analysis report using LLM"""
        try:
            if "error" in causal_results:
                return f"# Causal Analysis Report\n\n**Error:** {causal_results['error']}\n"
            
            # Import LLM service
            from modules.llm_service import llm_service
            
            # Prepare data for LLM
            llm_data = {
                "experiment_description": experiment_description,
                "causal_results": causal_results,
                "analysis_type": causal_results.get("analysis_type", "Causal Analysis"),
                "causal_estimate": causal_results.get("causal_estimate", {}),
                "refutation_test": causal_results.get("refutation_test", {}),
                "data_summary": causal_results.get("data_summary", {}),
                "endpoint_analyses": causal_results.get("endpoint_analyses", {})
            }
            
            # Generate report using LLM
            report_response = await llm_service.generate_causal_report(llm_data)
            
            if report_response["status"] == "success":
                return report_response["report"]
            else:
                # Fallback to simple report if LLM fails
                return self._generate_simple_causal_report(causal_results, experiment_description)
            
        except Exception as e:
            self.logger.error(f"Error generating causal report with LLM: {e}")
            # Fallback to simple report
            return self._generate_simple_causal_report(causal_results, experiment_description)
    
    def _generate_simple_causal_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Fallback simple causal report generation"""
        try:
            report = f"# Causal Analysis Report\n\n"
            report += f"**Experiment Description:** {experiment_description}\n\n"
            
            # Overall analysis
            if "analysis_type" in causal_results:
                report += f"## {causal_results['analysis_type']}\n\n"
                
                # Use full estimate object
                estimate = causal_results.get("causal_estimate", {})
                report += f"**Causal Estimate:** {estimate}\n\n"
                
                # Use full refute object
                refute = causal_results.get("refutation_test", {})
                report += f"**Refutation Test:** {refute}\n\n"
                
                data_summary = causal_results.get("data_summary", {})
                report += f"**Total Observations:** {data_summary.get('total_observations', 0)}\n"
                report += f"**Treatment Groups:** {data_summary.get('treatment_groups', 0)}\n\n"
            
            # Endpoint-specific analyses
            if "endpoint_analyses" in causal_results:
                report += "## Endpoint-Specific Analyses\n\n"
                
                for analysis_name, analysis_data in causal_results["endpoint_analyses"].items():
                    if "error" in analysis_data:
                        continue
                        
                    endpoint_name = analysis_name.split("_")[0]
                    metric_type = analysis_name.split("_")[1]
                    
                    report += f"### {endpoint_name} - {metric_type.title()}\n\n"
                    
                    estimate = analysis_data.get("causal_estimate", {})
                    report += f"**Causal Estimate:** {estimate}\n\n"
            
            # Recommendations
            report += "## Recommendations\n\n"
            report += self.generate_recommendations(causal_results)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating simple causal report: {e}")
            return f"# Causal Analysis Report\n\n**Error generating report:** {str(e)}\n"
    
    def serialize_dowhy_object(self, obj, visited=None) -> Dict[str, Any]:
        """Convert DoWhy objects to serializable dictionaries with recursion protection"""
        try:
            if visited is None:
                visited = set()
            
            if obj is None:
                return {}
            
            # Prevent infinite recursion by tracking visited objects
            obj_id = id(obj)
            if obj_id in visited:
                return {"circular_reference": str(type(obj).__name__)}
            
            visited.add(obj_id)
            
            # Try to get common DoWhy attributes first
            result = {}
            common_attrs = ['value', 'confidence_intervals', 'p_value', 'method_name', 'refutation_result', 'params']
            
            for attr in common_attrs:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if value is None:
                            result[attr] = None
                        elif isinstance(value, (str, int, float, bool)):
                            result[attr] = value
                        elif isinstance(value, (list, tuple)):
                            result[attr] = [self.serialize_dowhy_object(item, visited) if hasattr(item, '__dict__') else item for item in value]
                        elif hasattr(value, '__dict__'):
                            result[attr] = self.serialize_dowhy_object(value, visited)
                        else:
                            result[attr] = str(value)
                    except Exception as attr_error:
                        result[attr] = f"Error accessing {attr}: {str(attr_error)}"
            
            # If we got some attributes, return them
            if result:
                visited.remove(obj_id)
                return result
            
            # Fallback: try to convert to dictionary with limited recursion
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if key.startswith('_'):  # Skip private attributes
                        continue
                    try:
                        if isinstance(value, (str, int, float, bool)):
                            result[key] = value
                        elif isinstance(value, (list, tuple)):
                            result[key] = [self.serialize_dowhy_object(item, visited) if hasattr(item, '__dict__') else item for item in value[:5]]  # Limit list size
                        elif hasattr(value, '__dict__'):
                            result[key] = self.serialize_dowhy_object(value, visited)
                        else:
                            result[key] = str(value)
                    except Exception as key_error:
                        result[key] = f"Error accessing {key}: {str(key_error)}"
                
                visited.remove(obj_id)
                return result
            
            # Final fallback: string representation
            visited.remove(obj_id)
            return {"string_representation": str(obj), "type": str(type(obj).__name__)}
            
        except Exception as e:
            if 'visited' in locals() and obj_id in visited:
                visited.remove(obj_id)
            self.logger.error(f"Error serializing DoWhy object: {e}")
            return {"error": f"Serialization failed: {str(e)}", "string_representation": str(obj), "type": str(type(obj).__name__)}
    
    def generate_recommendations(self, causal_results: Dict[str, Any]) -> str:
        """Generate recommendations based on causal analysis results"""
        recommendations = []
        
        if "causal_estimate" in causal_results:
            estimate = causal_results["causal_estimate"]
            # Use full estimate object instead of specific attributes
            recommendations.append(f"- **Causal Estimate:** {estimate}")
        
        if "refutation_test" in causal_results:
            refute = causal_results["refutation_test"]
            # Use full refute object instead of specific attributes
            recommendations.append(f"- **Refutation Test:** {refute}")
        
        return "\n".join(recommendations) if recommendations else "- Causal analysis completed successfully"

# Create global instance
causal_analysis_engine = CausalAnalysisEngine()
