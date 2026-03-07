"""OpenTelemetry tracing integration for QueryReactor."""

import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
import logging

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None

from ..config.loader import config_loader

logger = logging.getLogger(__name__)


class TracingManager:
    """Manages OpenTelemetry tracing for QueryReactor."""
    
    def __init__(self):
        self.tracer = None
        self.enabled = False
        self._setup_tracing()
    
    def _setup_tracing(self) -> None:
        """Setup OpenTelemetry tracing if available and configured."""
        
        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry not available - tracing disabled")
            return
        
        # Check if tracing is enabled
        otel_endpoint = config_loader.get_env("OTEL_EXPORTER_OTLP_ENDPOINT")
        service_name = config_loader.get_env("OTEL_SERVICE_NAME", "queryreactor")
        
        if not otel_endpoint:
            logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set - tracing disabled")
            return
        
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: service_name,
                ResourceAttributes.SERVICE_VERSION: "1.0.0"
            })
            
            # Setup tracer provider
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)
            
            # Setup OTLP exporter
            otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            self.enabled = True
            
            logger.info(f"OpenTelemetry tracing enabled - Service: {service_name}, Endpoint: {otel_endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry tracing: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self.enabled and self.tracer is not None
    
    @contextmanager
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Start a new span with optional attributes."""
        
        if not self.is_enabled():
            yield None
            return
        
        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span
    
    def trace_module_execution(self, module_code: str):
        """Decorator to trace module execution."""
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.is_enabled():
                    return await func(*args, **kwargs)
                
                span_name = f"queryreactor.{module_code.lower()}"
                attributes = {
                    "queryreactor.module": module_code,
                    "queryreactor.operation": "execute"
                }
                
                # Extract request ID from state if available
                if args and hasattr(args[0], 'original_query'):
                    state = args[0]
                    attributes["queryreactor.request_id"] = str(state.original_query.id)
                    attributes["queryreactor.user_id"] = str(state.original_query.user_id)
                
                with self.start_span(span_name, attributes) as span:
                    start_time = time.time()
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        if span:
                            span.set_attribute("queryreactor.success", True)
                            span.set_attribute("queryreactor.duration_ms", 
                                             (time.time() - start_time) * 1000)
                        
                        return result
                        
                    except Exception as e:
                        if span:
                            span.set_attribute("queryreactor.success", False)
                            span.set_attribute("queryreactor.error", str(e))
                            span.record_exception(e)
                        raise
            
            return wrapper
        return decorator
    
    def add_query_context(self, span, state) -> None:
        """Add query context to span."""
        if not span or not state:
            return
        
        span.set_attribute("queryreactor.query.text", state.original_query.text)
        span.set_attribute("queryreactor.query.locale", state.original_query.locale or "unknown")
        span.set_attribute("queryreactor.workunits.count", len(state.workunits))
        
        if hasattr(state, 'evidences'):
            span.set_attribute("queryreactor.evidence.count", len(state.evidences))
        
        if hasattr(state, 'final_answer'):
            answer = state.final_answer
            if answer:
                span.set_attribute("queryreactor.answer.length", len(answer.text))
                span.set_attribute("queryreactor.answer.citations", len(answer.citations))
                span.set_attribute("queryreactor.answer.confidence", answer.confidence or 0.0)
    
    def trace_retrieval_path(self, path_id: str, workunit_count: int):
        """Create span for retrieval path execution."""
        
        if not self.is_enabled():
            return self._dummy_context_manager()
        
        span_name = f"queryreactor.retrieval.{path_id.lower()}"
        attributes = {
            "queryreactor.retrieval.path": path_id,
            "queryreactor.retrieval.workunits": workunit_count
        }
        
        return self.start_span(span_name, attributes)
    
    def trace_evidence_processing(self, operation: str, evidence_count: int):
        """Create span for evidence processing operations."""
        
        if not self.is_enabled():
            return self._dummy_context_manager()
        
        span_name = f"queryreactor.evidence.{operation}"
        attributes = {
            "queryreactor.evidence.operation": operation,
            "queryreactor.evidence.count": evidence_count
        }
        
        return self.start_span(span_name, attributes)
    
    @contextmanager
    def _dummy_context_manager(self):
        """Dummy context manager when tracing is disabled."""
        yield None


class MetricsCollector:
    """Collects performance metrics for QueryReactor."""
    
    def __init__(self):
        self.metrics = {}
        self.enabled = config_loader.get_config("metrics.enabled", True)
    
    def record_timing(self, operation: str, duration_ms: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric."""
        if not self.enabled:
            return
        
        metric_key = f"timing.{operation}"
        if metric_key not in self.metrics:
            self.metrics[metric_key] = []
        
        metric_data = {
            "duration_ms": duration_ms,
            "timestamp": int(time.time() * 1000),
            "labels": labels or {}
        }
        
        self.metrics[metric_key].append(metric_data)
        
        # Keep only last 1000 entries per metric
        if len(self.metrics[metric_key]) > 1000:
            self.metrics[metric_key] = self.metrics[metric_key][-1000:]
    
    def record_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Record counter metric."""
        if not self.enabled:
            return
        
        metric_key = f"counter.{name}"
        if metric_key not in self.metrics:
            self.metrics[metric_key] = 0
        
        self.metrics[metric_key] += value
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record gauge metric."""
        if not self.enabled:
            return
        
        metric_key = f"gauge.{name}"
        self.metrics[metric_key] = {
            "value": value,
            "timestamp": int(time.time() * 1000),
            "labels": labels or {}
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        summary = {
            "total_metrics": len(self.metrics),
            "counters": {},
            "gauges": {},
            "timing_stats": {}
        }
        
        for key, value in self.metrics.items():
            if key.startswith("counter."):
                name = key[8:]  # Remove "counter." prefix
                summary["counters"][name] = value
            elif key.startswith("gauge."):
                name = key[6:]  # Remove "gauge." prefix
                summary["gauges"][name] = value
            elif key.startswith("timing."):
                name = key[7:]  # Remove "timing." prefix
                if isinstance(value, list) and value:
                    durations = [item["duration_ms"] for item in value]
                    summary["timing_stats"][name] = {
                        "count": len(durations),
                        "avg_ms": sum(durations) / len(durations),
                        "min_ms": min(durations),
                        "max_ms": max(durations)
                    }
        
        return summary


# Global instances
tracing_manager = TracingManager()
metrics_collector = MetricsCollector()


def trace_module(module_code: str):
    """Decorator to trace module execution."""
    return tracing_manager.trace_module_execution(module_code)