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
    
    def create_experiment_dataframe(self, test_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create pandas DataFrame from test results for causal analysis"""
        try:
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
            
            # Estimate causal effect
            estimate = model.estimate_effect(
                identified_estimand, 
                method_name="backdoor.linear_regression"
            )
            
            # Refute the estimate
            refute = model.refute_estimate(
                identified_estimand, 
                estimate, 
                method_name="placebo_treatment_refuter"
            )
            
            # Extract results
            causal_results = {
                "analysis_type": analysis_name,
                "treatment_variable": "treatment",
                "outcome_variable": outcome_col,
                "causal_estimate": {
                    "value": float(estimate.value),
                    "confidence_interval": [
                        float(estimate.confidence_intervals[0][0]),
                        float(estimate.confidence_intervals[0][1])
                    ],
                    "p_value": float(estimate.p_value) if hasattr(estimate, 'p_value') else None
                },
                "refutation_test": {
                    "method": "placebo_treatment_refuter",
                    "refuted": refute.refute,
                    "new_effect": float(refute.new_effect) if hasattr(refute, 'new_effect') else None
                },
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
    
    def generate_causal_report(self, causal_results: Dict[str, Any], experiment_description: str) -> str:
        """Generate human-readable causal analysis report"""
        try:
            if "error" in causal_results:
                return f"# Causal Analysis Report\n\n**Error:** {causal_results['error']}\n"
            
            report = f"# Causal Analysis Report\n\n"
            report += f"**Experiment Description:** {experiment_description}\n\n"
            
            # Overall analysis
            if "analysis_type" in causal_results:
                report += f"## {causal_results['analysis_type']}\n\n"
                
                estimate = causal_results.get("causal_estimate", {})
                report += f"**Causal Effect:** {estimate.get('value', 'N/A'):.4f}\n"
                confidence_interval = estimate.get('confidence_interval', [0, 0])
                if len(confidence_interval) >= 2:
                    report += f"**Confidence Interval:** [{confidence_interval[0]:.4f}, {confidence_interval[1]:.4f}]\n"
                else:
                    report += f"**Confidence Interval:** N/A\n"
                report += f"**P-value:** {estimate.get('p_value', 'N/A')}\n\n"
                
                refute = causal_results.get("refutation_test", {})
                report += f"**Refutation Test:** {'Refuted' if refute.get('refuted', False) else 'Not Refuted'}\n\n"
                
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
                    report += f"**Causal Effect:** {estimate.get('value', 'N/A'):.4f}\n"
                    confidence_interval = estimate.get('confidence_interval', [])
                    if len(confidence_interval) >= 2:
                        report += f"**Confidence Interval:** [{confidence_interval[0]:.4f}, {confidence_interval[1]:.4f}]\n\n"
                    else:
                        report += f"**Confidence Interval:** N/A\n\n"
            
            # Recommendations
            report += "## Recommendations\n\n"
            report += self.generate_recommendations(causal_results)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating causal report: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return f"# Causal Analysis Report\n\n**Error generating report:** {str(e)}\n"
    
    def generate_recommendations(self, causal_results: Dict[str, Any]) -> str:
        """Generate recommendations based on causal analysis results"""
        recommendations = []
        
        if "causal_estimate" in causal_results:
            estimate = causal_results["causal_estimate"]
            effect_value = estimate.get("value", 0)
            
            if abs(effect_value) > 0.1:  # Significant effect
                if effect_value > 0:
                    recommendations.append(f"- **Significant positive effect detected** (effect size: {effect_value:.4f})")
                    recommendations.append("- Consider optimizing system performance to reduce this effect")
                else:
                    recommendations.append(f"- **Significant negative effect detected** (effect size: {effect_value:.4f})")
                    recommendations.append("- This treatment appears to improve performance")
            else:
                recommendations.append("- **No significant causal effect detected**")
                recommendations.append("- Treatment may not be the primary cause of performance changes")
        
        if "refutation_test" in causal_results:
            refute = causal_results["refutation_test"]
            if refute.get("refuted", False):
                recommendations.append("- **Causal effect was refuted by placebo test**")
                recommendations.append("- Results should be interpreted with caution")
            else:
                recommendations.append("- **Causal effect passed refutation test**")
                recommendations.append("- Results are more reliable")
        
        return "\n".join(recommendations) if recommendations else "- No specific recommendations available"

# Create global instance
causal_analysis_engine = CausalAnalysisEngine()
