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
            data_rows = []
            
            for i, result in enumerate(test_results):
                
                variation_name = result.get("variation_name", f"variation_{i}")
                total_requests = result.get("total_requests", 0)
                success_rate = result.get("success_rate", 0)
                avg_latency = result.get("avg_latency", 0)
                failure_rate = result.get("failure_rate", 0)
                
                
                treatment_level = self.extract_treatment_level(variation_name, result)
                
                
                results_data = result.get("results", {})
                endpoint_stats = results_data.get("endpoint_stats", {})
                
                
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
                            "timestamp": i * 30,  
                            "test_id": result.get("test_id", f"test_{i}")
                        })
                else:
                    
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
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error creating experiment DataFrame: {e}")
            raise
    
    def extract_treatment_level(self, variation_name: str, result: Dict[str, Any]) -> int:
        """Extract treatment level from variation name and result data"""
        variation_lower = variation_name.lower()
        
        
        if "baseline" in variation_lower or "control" in variation_lower:
            return 0
        else:
            return 1
    
    def analyze_multi_metric_causal_effect(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform multi-metric causal analysis (latency, success_rate, error_rate)"""
        try:
            if df.empty:
                self.logger.warning("Cannot perform multi-metric analysis - DataFrame is empty")
                return {
                    "latency_analysis": {"error": "No data available for latency analysis"},
                    "success_rate_analysis": {"error": "No data available for success rate analysis"},
                    "error_rate_analysis": {"error": "No data available for error rate analysis"},
                    "analysis_type": "Multi-Metric Analysis"
                }
            
            if len(df) < 2:
                self.logger.warning(f"Cannot perform multi-metric analysis - insufficient data (need at least 2 observations, got {len(df)})")
                return {
                    "latency_analysis": {"error": f"Insufficient data for latency analysis (need at least 2 observations, got {len(df)})"},
                    "success_rate_analysis": {"error": f"Insufficient data for success rate analysis (need at least 2 observations, got {len(df)})"},
                    "error_rate_analysis": {"error": f"Insufficient data for error rate analysis (need at least 2 observations, got {len(df)})"},
                    "analysis_type": "Multi-Metric Analysis"
                }
            
            latency_results = self.analyze_causal_effect(df, "latency")
            success_rate_results = self.analyze_causal_effect(df, "success_rate")
            error_rate_results = self.analyze_causal_effect(df, "error_rate")
            
            return {
                "latency_analysis": latency_results,
                "success_rate_analysis": success_rate_results,
                "error_rate_analysis": error_rate_results,
                "analysis_type": "Multi-Metric Analysis"
            }
            
        except Exception as e:
            self.logger.error(f"Error in multi-metric causal analysis: {e}")
            return {
                "latency_analysis": {"error": f"Multi-metric analysis failed: {str(e)}"},
                "success_rate_analysis": {"error": f"Multi-metric analysis failed: {str(e)}"},
                "error_rate_analysis": {"error": f"Multi-metric analysis failed: {str(e)}"},
                "analysis_type": "Multi-Metric Analysis"
            }
    
    def analyze_causal_effect(self, df: pd.DataFrame, analysis_type: str = "latency") -> Dict[str, Any]:
        """Perform causal analysis using DoWhy"""
        try:            
            if df.empty:
                return {"error": "No data available for causal analysis"}
            
            
            if analysis_type == "latency":
                outcome_col = "latency"
                analysis_name = "Latency Analysis"
            elif analysis_type == "success_rate":
                outcome_col = "success_rate"
                analysis_name = "Success Rate Analysis"
            elif analysis_type == "error_rate":
                outcome_col = "error_rate"
                analysis_name = "Error Rate Analysis"
                
                if outcome_col in df.columns:
                    error_rate_values = df[outcome_col].dropna()
                    if len(error_rate_values) == 0 or error_rate_values.nunique() <= 1:
                        return {
                            "analysis_type": analysis_name,
                            "treatment_variable": "treatment",
                            "outcome_variable": outcome_col,
                            "causal_estimate": {},
                            "refutation_test": {},
                            "data_summary": {
                                "total_observations": len(df),
                                "treatment_groups": df["treatment"].nunique(),
                                "endpoints": df["endpoint"].nunique(),
                                "error_rate_stats": {
                                    "min": error_rate_values.min() if len(error_rate_values) > 0 else 0,
                                    "max": error_rate_values.max() if len(error_rate_values) > 0 else 0,
                                    "mean": error_rate_values.mean() if len(error_rate_values) > 0 else 0,
                                    "unique_values": error_rate_values.nunique()
                                }
                            },
                            "note": "No error rate variation detected - all requests were successful. Causal analysis not applicable for error rate."
                        }
            else:
                outcome_col = "latency"
                analysis_name = "Latency Analysis"
            
            
            model = CausalModel(
                data=df,
                treatment="treatment",
                outcome=outcome_col,
                common_causes=[]  
            )
            
            identified_estimand = model.identify_effect()
            
            estimate = model.estimate_effect(
                identified_estimand, 
                method_name="backdoor.linear_regression"
            )
            
            refute = model.refute_estimate(
                identified_estimand, 
                estimate, 
                method_name="placebo_treatment_refuter"
            )       
            
            
            causal_results = {
                "analysis_type": analysis_name,
                "treatment_variable": "treatment",
                "outcome_variable": outcome_col,
                "causal_estimate": self.serialize_dowhy_object(estimate),  
                "refutation_test": self.serialize_dowhy_object(refute),      
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
                
                
                latency_analysis = self.analyze_causal_effect(endpoint_df, "latency")
                endpoint_analyses[f"{endpoint}_latency"] = latency_analysis
                
                
                success_analysis = self.analyze_causal_effect(endpoint_df, "success_rate")
                endpoint_analyses[f"{endpoint}_success"] = success_analysis
            
            return {
                "endpoint_analyses": endpoint_analyses,
                "summary": {
                    "total_endpoints": len(endpoints),
                    "analyzed_endpoints": len(endpoint_analyses) // 2  
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in multi-endpoint analysis: {e}")
            return {"error": f"Multi-endpoint analysis failed: {str(e)}"}
    
    async def generate_causal_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Generate human-readable causal analysis report using LLM"""
        try:
            
            if "analysis_type" in causal_results and causal_results["analysis_type"] == "Multi-Metric Analysis":
                return await self.generate_multi_metric_report(causal_results, experiment_description)
            
            
            if "error" in causal_results:
                return f"# Causal Analysis Report\n\n**Error:** {causal_results['error']}\n"
            
            
            from modules.llm_service import llm_service
            
            
            llm_data = {
                "experiment_description": experiment_description,
                "causal_results": causal_results,
                "analysis_type": causal_results.get("analysis_type", "Causal Analysis"),
                "causal_estimate": causal_results.get("causal_estimate", {}),
                "refutation_test": causal_results.get("refutation_test", {}),
                "data_summary": causal_results.get("data_summary", {}),
                "endpoint_analyses": causal_results.get("endpoint_analyses", {})
            }
            
            
            report_response = await llm_service.generate_causal_report(llm_data)
            
            if report_response["status"] == "success":
                return report_response["report"]
            else:
                
                return self.generate_simple_causal_report(causal_results, experiment_description)
            
        except Exception as e:
            self.logger.error(f"Error generating causal report with LLM: {e}")
            
            return self.generate_simple_causal_report(causal_results, experiment_description)
    
    async def generate_multi_metric_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Generate report for multi-metric causal analysis"""
        try:
            
            from modules.llm_service import llm_service
            
            
            llm_data = {
                "experiment_description": experiment_description,
                "analysis_type": "Multi-Metric Causal Analysis",
                "latency_analysis": causal_results.get("latency_analysis", {}),
                "success_rate_analysis": causal_results.get("success_rate_analysis", {}),
                "error_rate_analysis": causal_results.get("error_rate_analysis", {}),
                "multi_metric": True
            }
            
            
            report_response = await llm_service.generate_causal_report(llm_data)
            
            if report_response["status"] == "success":
                return report_response["report"]
            else:

                return self.generate_simple_multi_metric_report(causal_results, experiment_description)
            
        except Exception as e:
            self.logger.error(f"Error generating multi-metric causal report with LLM: {e}")

            return self.generate_simple_multi_metric_report(causal_results, experiment_description)
    
    def generate_simple_multi_metric_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Fallback simple multi-metric causal report generation"""
        try:
            report = f"# Multi-Metric Causal Analysis Report\n\n"
            report += f"**Experiment Description:** {experiment_description}\n\n"
            

            latency_analysis = causal_results.get("latency_analysis", {})
            if latency_analysis and "error" not in latency_analysis:
                report += f"## Latency Analysis\n\n"
                estimate = latency_analysis.get("causal_estimate", {})
                report += f"**Causal Effect on Latency:** {estimate}\n\n"
                refute = latency_analysis.get("refutation_test", {})
                report += f"**Refutation Test:** {refute}\n\n"
            

            success_analysis = causal_results.get("success_rate_analysis", {})
            if success_analysis and "error" not in success_analysis:
                report += f"## Success Rate Analysis\n\n"
                estimate = success_analysis.get("causal_estimate", {})
                report += f"**Causal Effect on Success Rate:** {estimate}\n\n"
                refute = success_analysis.get("refutation_test", {})
                report += f"**Refutation Test:** {refute}\n\n"
            

            error_analysis = causal_results.get("error_rate_analysis", {})
            if error_analysis and "error" not in error_analysis:
                report += f"## Error Rate Analysis\n\n"
                estimate = error_analysis.get("causal_estimate", {})
                report += f"**Causal Effect on Error Rate:** {estimate}\n\n"
                refute = error_analysis.get("refutation_test", {})
                report += f"**Refutation Test:** {refute}\n\n"
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating simple multi-metric report: {e}")
            return f"# Multi-Metric Causal Analysis Report\n\n**Error generating report:** {str(e)}\n"
    
    def generate_simple_causal_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Fallback simple causal report generation"""
        try:
            report = f"# Causal Analysis Report\n\n"
            report += f"**Experiment Description:** {experiment_description}\n\n"
            

            if "analysis_type" in causal_results:
                report += f"## {causal_results['analysis_type']}\n\n"
                

                estimate = causal_results.get("causal_estimate", {})
                report += f"**Causal Estimate:** {estimate}\n\n"
                

                refute = causal_results.get("refutation_test", {})
                report += f"**Refutation Test:** {refute}\n\n"
                
                data_summary = causal_results.get("data_summary", {})
                report += f"**Total Observations:** {data_summary.get('total_observations', 0)}\n"
                report += f"**Treatment Groups:** {data_summary.get('treatment_groups', 0)}\n\n"
            

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
            

            obj_id = id(obj)
            if obj_id in visited:
                return {"circular_reference": str(type(obj).__name__)}
            
            visited.add(obj_id)
            

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
            
        
            if result:
                visited.remove(obj_id)
                return result
            
        
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if key.startswith('_'):  
                        continue
                    try:
                        if isinstance(value, (str, int, float, bool)):
                            result[key] = value
                        elif isinstance(value, (list, tuple)):
                            result[key] = [self.serialize_dowhy_object(item, visited) if hasattr(item, '__dict__') else item for item in value[:5]]  
                        elif hasattr(value, '__dict__'):
                            result[key] = self.serialize_dowhy_object(value, visited)
                        else:
                            result[key] = str(value)
                    except Exception as key_error:
                        result[key] = f"Error accessing {key}: {str(key_error)}"
                
                visited.remove(obj_id)
                return result
            
        
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

            recommendations.append(f"- **Causal Estimate:** {estimate}")
        
        if "refutation_test" in causal_results:
            refute = causal_results["refutation_test"]

            recommendations.append(f"- **Refutation Test:** {refute}")
        
        return "\n".join(recommendations) if recommendations else "- Causal analysis completed successfully"


causal_analysis_engine = CausalAnalysisEngine()
