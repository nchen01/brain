"""Performance metrics collection for QueryReactor."""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimingMetric:
    """Represents a timing measurement."""
    operation: str
    duration_ms: float
    timestamp: int
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class CounterMetric:
    """Represents a counter measurement."""
    name: str
    value: int
    timestamp: int
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""
    query_id: str
    user_id: str
    start_time: int
    end_time: Optional[int] = None
    total_duration_ms: Optional[float] = None
    
    # Module execution times
    module_timings: Dict[str, float] = field(default_factory=dict)
    
    # Evidence metrics
    evidence_retrieved: int = 0
    evidence_after_quality_check: int = 0
    evidence_after_aggregation: int = 0
    evidence_after_ranking: int = 0
    
    # Path metrics
    paths_used: List[str] = field(default_factory=list)
    path_timings: Dict[str, float] = field(default_factory=dict)
    path_success: Dict[str, bool] = field(default_factory=dict)
    
    # Loop metrics
    loop_iterations: Dict[str, int] = field(default_factory=dict)
    
    # Answer metrics
    answer_length: Optional[int] = None
    answer_citations: Optional[int] = None
    answer_confidence: Optional[float] = None
    verification_success: Optional[bool] = None
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    
    def finalize(self) -> None:
        """Finalize metrics calculation."""
        if self.end_time and self.start_time:
            self.total_duration_ms = self.end_time - self.start_time
    
    def add_module_timing(self, module_code: str, duration_ms: float) -> None:
        """Add module execution timing."""
        self.module_timings[module_code] = duration_ms
    
    def add_path_timing(self, path_id: str, duration_ms: float, success: bool = True) -> None:
        """Add path execution timing."""
        if path_id not in self.paths_used:
            self.paths_used.append(path_id)
        self.path_timings[path_id] = duration_ms
        self.path_success[path_id] = success
    
    def add_loop_iteration(self, loop_type: str) -> None:
        """Record a loop iteration."""
        self.loop_iterations[loop_type] = self.loop_iterations.get(loop_type, 0) + 1
    
    def add_error(self, error_message: str) -> None:
        """Add error to tracking."""
        self.errors.append(error_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query_id": self.query_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "module_timings": self.module_timings,
            "evidence_metrics": {
                "retrieved": self.evidence_retrieved,
                "after_quality_check": self.evidence_after_quality_check,
                "after_aggregation": self.evidence_after_aggregation,
                "after_ranking": self.evidence_after_ranking
            },
            "path_metrics": {
                "paths_used": self.paths_used,
                "path_timings": self.path_timings,
                "path_success": self.path_success
            },
            "loop_metrics": self.loop_iterations,
            "answer_metrics": {
                "length": self.answer_length,
                "citations": self.answer_citations,
                "confidence": self.answer_confidence,
                "verification_success": self.verification_success
            },
            "errors": self.errors
        }


class PerformanceMonitor:
    """Monitors and collects performance metrics."""
    
    def __init__(self):
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.global_timings: Dict[str, List[float]] = defaultdict(list)
        self.global_counters: Dict[str, int] = defaultdict(int)
        self.enabled = True
    
    def start_query_tracking(self, query_id: str, user_id: str) -> None:
        """Start tracking metrics for a query."""
        if not self.enabled:
            return
        
        self.query_metrics[query_id] = QueryMetrics(
            query_id=query_id,
            user_id=user_id,
            start_time=int(time.time() * 1000)
        )
    
    def end_query_tracking(self, query_id: str) -> Optional[QueryMetrics]:
        """End tracking for a query and return metrics."""
        if not self.enabled or query_id not in self.query_metrics:
            return None
        
        metrics = self.query_metrics[query_id]
        metrics.end_time = int(time.time() * 1000)
        metrics.finalize()
        
        # Add to global statistics
        if metrics.total_duration_ms:
            self.global_timings["query_total"].append(metrics.total_duration_ms)
        
        self.global_counters["queries_processed"] += 1
        
        if metrics.errors:
            self.global_counters["queries_with_errors"] += 1
        
        return metrics
    
    def record_module_execution(self, query_id: str, module_code: str, duration_ms: float) -> None:
        """Record module execution timing."""
        if not self.enabled:
            return
        
        # Add to query-specific metrics
        if query_id in self.query_metrics:
            self.query_metrics[query_id].add_module_timing(module_code, duration_ms)
        
        # Add to global statistics
        self.global_timings[f"module_{module_code.lower()}"].append(duration_ms)
    
    def record_path_execution(self, query_id: str, path_id: str, duration_ms: float, 
                            evidence_count: int, success: bool = True) -> None:
        """Record retrieval path execution."""
        if not self.enabled:
            return
        
        # Add to query-specific metrics
        if query_id in self.query_metrics:
            self.query_metrics[query_id].add_path_timing(path_id, duration_ms, success)
        
        # Add to global statistics
        self.global_timings[f"path_{path_id.lower()}"].append(duration_ms)
        self.global_counters[f"path_{path_id.lower()}_executions"] += 1
        
        if success:
            self.global_counters[f"path_{path_id.lower()}_success"] += 1
        
        self.global_timings["evidence_retrieval"].append(evidence_count)
    
    def record_evidence_processing(self, query_id: str, stage: str, evidence_count: int) -> None:
        """Record evidence processing metrics."""
        if not self.enabled or query_id not in self.query_metrics:
            return
        
        metrics = self.query_metrics[query_id]
        
        if stage == "retrieved":
            metrics.evidence_retrieved = evidence_count
        elif stage == "quality_check":
            metrics.evidence_after_quality_check = evidence_count
        elif stage == "aggregation":
            metrics.evidence_after_aggregation = evidence_count
        elif stage == "ranking":
            metrics.evidence_after_ranking = evidence_count
        
        # Global statistics
        self.global_timings[f"evidence_{stage}"].append(evidence_count)
    
    def record_loop_iteration(self, query_id: str, loop_type: str) -> None:
        """Record loop iteration."""
        if not self.enabled:
            return
        
        if query_id in self.query_metrics:
            self.query_metrics[query_id].add_loop_iteration(loop_type)
        
        self.global_counters[f"loop_{loop_type}"] += 1
    
    def record_answer_metrics(self, query_id: str, answer_length: int, citations_count: int, 
                            confidence: float, verification_success: bool) -> None:
        """Record answer generation metrics."""
        if not self.enabled or query_id not in self.query_metrics:
            return
        
        metrics = self.query_metrics[query_id]
        metrics.answer_length = answer_length
        metrics.answer_citations = citations_count
        metrics.answer_confidence = confidence
        metrics.verification_success = verification_success
        
        # Global statistics
        self.global_timings["answer_length"].append(answer_length)
        self.global_timings["answer_citations"].append(citations_count)
        self.global_timings["answer_confidence"].append(confidence)
        
        if verification_success:
            self.global_counters["verification_success"] += 1
        else:
            self.global_counters["verification_failure"] += 1
    
    def record_error(self, query_id: str, error_message: str) -> None:
        """Record error occurrence."""
        if not self.enabled:
            return
        
        if query_id in self.query_metrics:
            self.query_metrics[query_id].add_error(error_message)
        
        self.global_counters["total_errors"] += 1
    
    def get_query_metrics(self, query_id: str) -> Optional[QueryMetrics]:
        """Get metrics for a specific query."""
        return self.query_metrics.get(query_id)
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global performance statistics."""
        stats = {
            "counters": dict(self.global_counters),
            "timing_statistics": {}
        }
        
        for operation, timings in self.global_timings.items():
            if timings:
                stats["timing_statistics"][operation] = {
                    "count": len(timings),
                    "mean": statistics.mean(timings),
                    "median": statistics.median(timings),
                    "min": min(timings),
                    "max": max(timings),
                    "std_dev": statistics.stdev(timings) if len(timings) > 1 else 0.0
                }
        
        return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        stats = self.get_global_statistics()
        
        summary = {
            "queries_processed": self.global_counters.get("queries_processed", 0),
            "error_rate": 0.0,
            "average_query_time_ms": 0.0,
            "average_evidence_retrieved": 0.0,
            "path_usage": {},
            "loop_frequency": {}
        }
        
        # Calculate error rate
        total_queries = self.global_counters.get("queries_processed", 0)
        queries_with_errors = self.global_counters.get("queries_with_errors", 0)
        
        if total_queries > 0:
            summary["error_rate"] = queries_with_errors / total_queries
        
        # Average query time
        if "query_total" in stats["timing_statistics"]:
            summary["average_query_time_ms"] = stats["timing_statistics"]["query_total"]["mean"]
        
        # Average evidence retrieved
        if "evidence_retrieved" in stats["timing_statistics"]:
            summary["average_evidence_retrieved"] = stats["timing_statistics"]["evidence_retrieved"]["mean"]
        
        # Path usage statistics
        for counter_name, count in self.global_counters.items():
            if counter_name.startswith("path_") and counter_name.endswith("_executions"):
                path_id = counter_name.replace("path_", "").replace("_executions", "").upper()
                success_count = self.global_counters.get(f"path_{path_id.lower()}_success", 0)
                
                summary["path_usage"][path_id] = {
                    "executions": count,
                    "success_rate": success_count / count if count > 0 else 0.0
                }
        
        # Loop frequency
        for counter_name, count in self.global_counters.items():
            if counter_name.startswith("loop_"):
                loop_type = counter_name.replace("loop_", "")
                summary["loop_frequency"][loop_type] = count
        
        return summary
    
    def clear_old_metrics(self, max_age_hours: int = 24) -> None:
        """Clear old query metrics to prevent memory buildup."""
        if not self.enabled:
            return
        
        current_time = int(time.time() * 1000)
        max_age_ms = max_age_hours * 60 * 60 * 1000
        
        old_queries = []
        for query_id, metrics in self.query_metrics.items():
            if current_time - metrics.start_time > max_age_ms:
                old_queries.append(query_id)
        
        for query_id in old_queries:
            del self.query_metrics[query_id]
        
        if old_queries:
            logger.info(f"Cleared {len(old_queries)} old query metrics")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()