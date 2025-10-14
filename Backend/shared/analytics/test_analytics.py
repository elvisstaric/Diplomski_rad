import statistics
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class TestAnalytics:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_test_data(self, test_result: Dict[str, Any]):
        try:
            test_summary = self.extract_test_summary(test_result)
            
            endpoint_stats = self.analyze_endpoint_stats(test_result)
            
            error_patterns = self.analyze_error_patterns(test_result)
            
            time_series_data = self.extract_time_series_data(test_result)
            
            performance_insights = self.generate_performance_insights(
                test_summary, endpoint_stats, error_patterns
            )
            
            recommendations = self.generate_recommendations(
                test_summary, endpoint_stats, error_patterns
            )
            
            return {
                "test_id": test_result.get("test_id"),
                "test_summary": test_summary,
                "endpoint_stats": endpoint_stats,
                "error_patterns": error_patterns,
                "time_series_data": time_series_data,
                "performance_insights": performance_insights,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing test data: {e}")
            return self.get_default_analysis(test_result)
    
    def extract_test_summary(self, test_result: Dict[str, Any]):
        total_requests = test_result.get("total_requests", 0)
        successful_requests = test_result.get("successful_requests", 0)
        failed_requests = test_result.get("failed_requests", 0)
        
        start_time = test_result.get("start_time")
        end_time = test_result.get("end_time")
        duration = 0
        if start_time and end_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = int((end_time - start_time).total_seconds())
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        failure_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        avg_latency = test_result.get("avg_latency", 0)
        max_latency = test_result.get("max_latency", 0)
        min_latency = test_result.get("min_latency", 0)
        latency_variance = test_result.get("latency_variance", 0)
        
        return {
            "duration": duration,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "avg_latency": round(avg_latency, 3),
            "max_latency": round(max_latency, 3),
            "min_latency": round(min_latency, 3),
            "latency_variance": round(latency_variance, 3),
            "requests_per_second": round(total_requests / duration, 2) if duration > 0 else 0
        }
    
    def analyze_endpoint_stats(self, test_result: Dict[str, Any]):
        endpoint_stats = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "errors": [],
            "latencies": [],
            "error_categories": Counter(),
            "error_severities": Counter(),
            "time_patterns": []
        })
        
        error_details = test_result.get("error_details", [])
        
        for error in error_details:
            endpoint = error.get("endpoint", "unknown")
            endpoint_stats[endpoint]["failed_requests"] += 1
            endpoint_stats[endpoint]["errors"].append(error)
            endpoint_stats[endpoint]["error_categories"][error.get("category", "unknown")] += 1
            endpoint_stats[endpoint]["error_severities"][error.get("severity", "unknown")] += 1
            
            timestamp = error.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    endpoint_stats[endpoint]["time_patterns"].append(dt)
                except Exception as e:
                    self.logger.warning(f"Error parsing timestamp {timestamp}: {e}")
        
        
        result = {}
        for endpoint, stats in endpoint_stats.items():
            total_requests = stats["total_requests"]
            failed_requests = stats["failed_requests"]
            
            successful_requests = max(0, total_requests - failed_requests)
            
            result[endpoint] = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2),
                "failure_rate": round((failed_requests / total_requests * 100) if total_requests > 0 else 0, 2),
                "error_categories": dict(stats["error_categories"]),
                "error_severities": dict(stats["error_severities"]),
                "time_patterns": [dt.isoformat() for dt in stats["time_patterns"]],
                "most_common_error": stats["error_categories"].most_common(1)[0] if stats["error_categories"] else None,
                "critical_errors": stats["error_severities"].get("critical", 0) + stats["error_severities"].get("high", 0)
            }
        
        return result
    
    def analyze_error_patterns(self, test_result: Dict[str, Any]):
        
        error_details = test_result.get("error_details", [])
        if not error_details:
            return []
        
        patterns = []
        
        
        category_groups = defaultdict(list)
        for error in error_details:
            category = error.get("category", "unknown")
            category_groups[category].append(error)
        
        
        for category, errors in category_groups.items():
            pattern = {
                "category": category,
                "count": len(errors),
                "percentage": round(len(errors) / len(error_details) * 100, 2),
                "endpoints": list(set(error.get("endpoint", "unknown") for error in errors)),
                "severity_distribution": Counter(error.get("severity", "unknown") for error in errors),
                "time_distribution": self.analyze_time_distribution(errors),
                "common_error_messages": self.extract_common_messages(errors)
            }
            patterns.append(pattern)
        
        
        patterns.sort(key=lambda x: x["count"], reverse=True)
        
        return patterns
    
    def analyze_time_distribution(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        
        if not errors:
            return {}
        
        timestamps = []
        for error in errors:
            timestamp = error.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    timestamps.append(dt)
                except Exception:
                    continue
        
        if not timestamps:
            return {}
        
        timestamps.sort()
        
        
        if len(timestamps) > 1:
            intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            avg_interval = statistics.mean(intervals) if intervals else 0
        else:
            avg_interval = 0
        
        return {
            "first_error": timestamps[0].isoformat() if timestamps else None,
            "last_error": timestamps[-1].isoformat() if timestamps else None,
            "error_count": len(timestamps),
            "avg_interval_seconds": round(avg_interval, 2),
            "time_span_seconds": round((timestamps[-1] - timestamps[0]).total_seconds(), 2) if len(timestamps) > 1 else 0
        }
    
    def extract_common_messages(self, errors: List[Dict[str, Any]]) :
        
        messages = [error.get("error_message", "") for error in errors if error.get("error_message")]
        message_counts = Counter(messages)
        return message_counts.most_common(3)
    
    def extract_time_series_data(self, test_result: Dict[str, Any]) -> Dict[str, List[float]]:

        error_details = test_result.get("error_details", [])
        
        time_intervals = defaultdict(int)
        
        for error in error_details:
            timestamp = error.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    
                    
                    interval = int(dt.timestamp() // 10) * 10
                    time_intervals[interval] += 1
                except Exception:
                    continue
        
        
        sorted_intervals = sorted(time_intervals.items())
        error_counts = [count for _, count in sorted_intervals]
        
        return {
            "error_counts_over_time": error_counts,
            "time_intervals": [timestamp for timestamp, _ in sorted_intervals]
        }
    
    def generate_performance_insights(self, test_summary: Dict[str, Any], 
                                     endpoint_stats: Dict[str, Dict[str, Any]], 
                                     error_patterns: List[Dict[str, Any]]):
        insights = []
        
        
        success_rate = test_summary.get("success_rate", 0)
        if success_rate < 90:
            insights.append(f"Low success rate ({success_rate}%) indicates significant performance issues")
        elif success_rate < 95:
            insights.append(f"Moderate success rate ({success_rate}%) suggests some performance concerns")
        else:
            insights.append(f"Good success rate ({success_rate}%) indicates stable performance")
        
        
        avg_latency = test_summary.get("avg_latency", 0)
        if avg_latency > 2.0:
            insights.append(f"High average latency ({avg_latency}s) suggests performance bottlenecks")
        elif avg_latency > 1.0:
            insights.append(f"Moderate latency ({avg_latency}s) may impact user experience")
        
        
        if error_patterns:
            top_error = error_patterns[0]
            insights.append(f"Most common error type: {top_error['category']} ({top_error['count']} occurrences)")
            
            if top_error['percentage'] > 50:
                insights.append(f"Error type '{top_error['category']}' represents {top_error['percentage']}% of all errors")
        
        
        for endpoint, stats in endpoint_stats.items():
            if stats.get("failure_rate", 0) > 20:
                insights.append(f"Endpoint {endpoint} has high failure rate ({stats['failure_rate']}%)")
            
            critical_errors = stats.get("critical_errors", 0)
            if critical_errors > 0:
                insights.append(f"Endpoint {endpoint} has {critical_errors} critical/high severity errors")
        
        return insights
    
    def generate_recommendations(self, test_summary: Dict[str, Any], 
                                endpoint_stats: Dict[str, Dict[str, Any]], 
                                error_patterns: List[Dict[str, Any]]):
        recommendations = []
        
        
        success_rate = test_summary.get("success_rate", 0)
        if success_rate < 90:
            recommendations.append("Investigate and fix critical errors causing low success rate")
            recommendations.append("Consider implementing retry mechanisms for transient failures")
        
        
        avg_latency = test_summary.get("avg_latency", 0)
        if avg_latency > 2.0:
            recommendations.append("Optimize database queries and implement caching to reduce latency")
            recommendations.append("Consider horizontal scaling or load balancing")
        
        
        for pattern in error_patterns:
            category = pattern["category"]
            if category == "timeout":
                recommendations.append("Increase timeout values or optimize slow operations")
            elif category == "network":
                recommendations.append("Implement connection pooling and retry mechanisms")
            elif category == "server_error":
                recommendations.append("Investigate server-side issues and implement proper error handling")
            elif category == "auth_error":
                recommendations.append("Review authentication logic and token management")
        
        
        for endpoint, stats in endpoint_stats.items():
            failure_rate = stats.get("failure_rate", 0)
            if failure_rate > 20:
                recommendations.append(f"Priority: Fix issues with endpoint {endpoint} (failure rate: {failure_rate}%)")
        
        
        if not recommendations:
            recommendations.append("Performance is within acceptable limits")
            recommendations.append("Continue monitoring for any degradation trends")
        
        return recommendations
    
    def get_default_analysis(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        
        return {
            "test_id": test_result.get("test_id", "unknown"),
            "test_summary": {
                "duration": 0,
                "total_requests": test_result.get("total_requests", 0),
                "successful_requests": test_result.get("successful_requests", 0),
                "failed_requests": test_result.get("failed_requests", 0),
                "success_rate": 0,
                "failure_rate": 0,
                "avg_latency": 0,
                "max_latency": 0,
                "min_latency": 0,
                "requests_per_second": 0
            },
            "endpoint_stats": {},
            "error_patterns": [],
            "time_series_data": {},
            "performance_insights": ["Analysis failed - using default data"],
            "recommendations": ["Unable to generate recommendations due to analysis error"]
        }
