"""Main API service for QueryReactor."""

import asyncio
import time
from typing import Dict, Any, Optional
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    QueryRequest, QueryResponse, ErrorResponse, HealthResponse,
    MetricsResponse, FeedbackRequest, FeedbackResponse,
    CitationResponse, ProcessingMetadata, VerificationInfo,
    QARequest, QAResponse,
    DirectAskRequest, DirectAskResponse, DirectChunkSource,
)
from ..models import UserQuery, ContextBundle
from ..workflow.graph import query_reactor_graph
from ..config.loader import config_loader
from ..logging.setup import setup_logging, get_request_logger
from ..observability.metrics import performance_monitor
from ..observability.tracing import tracing_manager

# Setup logging
setup_logging()
logger = logging.getLogger("queryreactor.api")


class QueryReactorService:
    """Main service class for QueryReactor API."""
    
    def __init__(self):
        self.app = FastAPI(
            title="QueryReactor API",
            description="Production-ready smart query and question-answering system",
            version="1.0.0"
        )
        self._setup_middleware()
        self._setup_routes()
        self._load_config()
    
    def _setup_middleware(self) -> None:
        """Setup FastAPI middleware."""
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self) -> None:
        """Setup API routes."""
        
        @self.app.post("/api/query", response_model=QueryResponse)
        async def process_query(request: QueryRequest, background_tasks: BackgroundTasks):
            """Process a user query and return answer with citations."""
            return await self._process_query(request, background_tasks)
        
        @self.app.get("/api/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return await self._health_check()
        
        @self.app.get("/api/metrics", response_model=MetricsResponse)
        async def get_metrics():
            """Get system performance metrics."""
            return await self._get_metrics()
        
        @self.app.post("/api/feedback", response_model=FeedbackResponse)
        async def submit_feedback(request: FeedbackRequest):
            """Submit feedback for a query response."""
            return await self._submit_feedback(request)
        
        @self.app.get("/api/query/{query_id}/status")
        async def get_query_status(query_id: str):
            """Get status of a specific query (for long-running queries)."""
            return await self._get_query_status(query_id)

        @self.app.post("/api/ask-direct", response_model=DirectAskResponse)
        async def ask_direct(request: DirectAskRequest):
            """Direct RAG endpoint: brain-mvp search → GPT synthesis, no pipeline."""
            return await self._direct_rag(request)

        @self.app.post("/api/qa", response_model=QAResponse)
        async def qa_query(request: QARequest, background_tasks: BackgroundTasks):
            """QA endpoint backed by brain-mvp knowledge base."""
            query_request = QueryRequest(
                text=request.question,
                user_id=request.user_id,
                locale=request.locale,
            )
            base_response = await self._process_query(query_request, background_tasks)
            return await self._create_qa_response(base_response)
        
        # Error handlers
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc):
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    error="HTTP_ERROR",
                    message=exc.detail,
                    timestamp=int(time.time() * 1000)
                ).dict()
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request, exc):
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="INTERNAL_ERROR",
                    message="An internal error occurred while processing your request",
                    timestamp=int(time.time() * 1000)
                ).dict()
            )
    
    def _load_config(self) -> None:
        """Load configuration settings."""
        config_loader.load_all()
        self.config = config_loader.config
        logger.info("Configuration loaded successfully")
    
    async def _process_query(self, request: QueryRequest, background_tasks: BackgroundTasks) -> QueryResponse:
        """Process a user query through the QueryReactor workflow."""
        
        # Generate query ID and setup tracking
        query_id = str(uuid4())
        request_logger = get_request_logger(query_id)
        
        try:
            # Start performance monitoring
            performance_monitor.start_query_tracking(query_id, str(request.user_id))
            
            request_logger.info(f"Processing query: {request.text[:100]}...")
            
            # Create UserQuery object
            user_query = UserQuery(
                user_id=request.user_id or uuid4(),
                conversation_id=request.conversation_id or uuid4(),
                text=request.text,
                locale=request.locale,
                context=ContextBundle(
                    user_metadata=request.context
                ) if request.context else None
            )
            
            # Process through workflow
            with tracing_manager.start_span("queryreactor.query_processing") as span:
                if span:
                    span.set_attribute("queryreactor.query.id", str(user_query.id))
                    span.set_attribute("queryreactor.query.text", request.text)
                
                result_state = await query_reactor_graph.process_query(
                    query_data=user_query.dict(),
                    config=self.config
                )
                
                if span:
                    tracing_manager.add_query_context(span, result_state)
            
            # Convert to API response
            response = await self._create_response(result_state, query_id)
            
            # Record metrics
            if result_state.final_answer:
                answer = result_state.final_answer
                performance_monitor.record_answer_metrics(
                    query_id=query_id,
                    answer_length=len(answer.text),
                    citations_count=len(answer.citations),
                    confidence=answer.confidence or 0.0,
                    verification_success=getattr(result_state, 'verification_result', None) is not None
                )
            
            # End performance monitoring
            performance_monitor.end_query_tracking(query_id)
            
            request_logger.info(f"Query processed successfully - Answer length: {len(response.answer)}")
            
            # Schedule cleanup in background
            background_tasks.add_task(self._cleanup_query_data, query_id)
            
            return response
            
        except Exception as e:
            # Record error
            performance_monitor.record_error(query_id, str(e))
            performance_monitor.end_query_tracking(query_id)
            
            request_logger.error(f"Query processing failed: {e}")
            
            raise HTTPException(
                status_code=500,
                detail=f"Query processing failed: {str(e)}"
            )
    
    async def _create_response(self, state, query_id: str) -> QueryResponse:
        """Create API response from workflow state."""
        
        if not state.final_answer:
            raise HTTPException(
                status_code=500,
                detail="No answer was generated"
            )
        
        answer = state.final_answer
        
        # Format citations
        citations = []
        formatted_answer = getattr(state, 'formatted_answer', None)
        if formatted_answer and isinstance(formatted_answer, dict) and formatted_answer.get('citations'):
            for citation_data in formatted_answer['citations']:
                citations.append(CitationResponse(**citation_data))
        
        # Create metadata
        metadata = ProcessingMetadata(
            workunits_processed=len(state.workunits),
            evidence_items_found=len(state.evidences),
            retrieval_paths_used=list(set(e.provenance.retrieval_path for e in state.evidences)),
            processing_time_ms=getattr(state, 'total_processing_time_ms', None)
        )
        
        # Create verification info if available
        verification = None
        verification_result = getattr(state, 'verification_result', None)
        if verification_result is not None:
            verification = VerificationInfo(
                is_valid=getattr(verification_result, 'is_valid', True),
                confidence=getattr(verification_result, 'confidence', 1.0),
                issues_count=len(verification_result.issues) if getattr(verification_result, 'issues', None) else 0
            )
        
        return QueryResponse(
            query_id=query_id,
            answer=answer.text,
            confidence=answer.confidence or 0.0,
            citations=citations,
            limitations=answer.limitations or [],
            metadata=metadata,
            verification=verification
        )
    
    async def _health_check(self) -> HealthResponse:
        """Perform health check."""
        
        components = {
            "workflow": "healthy",
            "config": "healthy",
            "tracing": "healthy" if tracing_manager.is_enabled() else "disabled",
            "metrics": "healthy" if performance_monitor.enabled else "disabled"
        }
        
        # Test workflow initialization
        try:
            if query_reactor_graph.graph is None:
                components["workflow"] = "unhealthy"
        except Exception:
            components["workflow"] = "unhealthy"
        
        # Determine overall status
        overall_status = "healthy" if all(
            status in ["healthy", "disabled"] for status in components.values()
        ) else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            version="1.0.0",
            components=components
        )
    
    async def _get_metrics(self) -> MetricsResponse:
        """Get performance metrics."""
        
        summary = performance_monitor.get_performance_summary()
        
        return MetricsResponse(
            queries_processed=summary.get("queries_processed", 0),
            error_rate=summary.get("error_rate", 0.0),
            average_query_time_ms=summary.get("average_query_time_ms", 0.0),
            average_evidence_retrieved=summary.get("average_evidence_retrieved", 0.0),
            path_usage=summary.get("path_usage", {}),
            loop_frequency=summary.get("loop_frequency", {})
        )
    
    async def _submit_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        """Submit user feedback."""
        
        # In V1.0, this is a placeholder
        # In V1.1, this would integrate with feedback storage system
        
        logger.info(f"Feedback received for query {request.query_id}: {request.feedback_type}")
        
        return FeedbackResponse(
            success=True,
            message="Feedback recorded successfully"
        )
    
    async def _get_query_status(self, query_id: str) -> Dict[str, Any]:
        """Get status of a specific query."""
        
        # Get metrics for the query if available
        metrics = performance_monitor.get_query_metrics(query_id)
        
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail="Query not found"
            )
        
        return {
            "query_id": query_id,
            "status": "completed" if metrics.end_time else "processing",
            "start_time": metrics.start_time,
            "end_time": metrics.end_time,
            "duration_ms": metrics.total_duration_ms,
            "evidence_count": metrics.evidence_retrieved,
            "paths_used": metrics.paths_used,
            "errors": metrics.errors
        }
    
    async def _create_qa_response(self, base: QueryResponse) -> QAResponse:
        """Wrap a QueryResponse as a QAResponse, adding doc_sources."""
        # Collect unique source_ids from citations (set by brain-mvp provenance)
        doc_sources = list(dict.fromkeys(
            c.source for c in base.citations
            if c.source_type == "db" and c.source
        ))
        return QAResponse(
            query_id=base.query_id,
            answer=base.answer,
            confidence=base.confidence,
            citations=base.citations,
            limitations=base.limitations,
            metadata=base.metadata,
            verification=base.verification,
            timestamp=base.timestamp,
            doc_sources=doc_sources,
        )

    async def _direct_rag(self, request: DirectAskRequest) -> DirectAskResponse:
        """Direct RAG: retrieve chunks from brain-mvp then synthesize with GPT in one call."""
        from uuid import uuid4 as _uuid4
        from ..services.brain_retriever import brain_retriever

        query_id = str(_uuid4())

        # 1. Retrieve chunks from brain-mvp
        hits = await brain_retriever.search(
            query=request.question,
            top_k=request.top_k,
            doc_filter=request.doc_filter,
        )

        if not hits:
            return DirectAskResponse(
                query_id=query_id,
                answer="No relevant documents found in the knowledge base. Please upload documents first.",
                sources=[],
                doc_sources=[],
            )

        # 2. Build context from top chunks
        context_parts = []
        sources = []
        seen_chunks = set()
        for hit in hits:
            chunk = hit.get("chunk", hit)  # brain-mvp wraps hit under "chunk" key
            chunk_id = chunk.get("chunk_id") or hit.get("chunk_id", "")
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)

            doc_uuid = chunk.get("doc_uuid") or hit.get("doc_uuid", "")
            score = float(hit.get("score", 0.0))
            metadata = chunk.get("metadata") or hit.get("metadata") or {}
            section_path = metadata.get("section_path", "")
            content = (
                chunk.get("enriched_content")
                or chunk.get("original_content")
                or hit.get("enriched_content")
                or hit.get("original_content")
                or ""
            )

            if not content:
                continue

            context_parts.append(
                f"[Source: {section_path or doc_uuid}]\n{content}"
            )
            sources.append(DirectChunkSource(
                chunk_id=chunk_id,
                doc_uuid=doc_uuid,
                score=score,
                section_path=section_path or None,
                content_preview=content[:300],
            ))

        if not context_parts:
            return DirectAskResponse(
                query_id=query_id,
                answer="Retrieved chunks had no content. Please check that documents are processed.",
                sources=[],
                doc_sources=[],
            )

        context_text = "\n\n---\n\n".join(context_parts)

        # 3. Synthesize with GPT
        system_prompt = (
            "You are a helpful assistant that answers questions based strictly on the provided document excerpts. "
            "Always ground your answer in the sources below. If the answer is not in the sources, say so clearly."
        )
        user_prompt = (
            f"Document excerpts:\n\n{context_text}\n\n"
            f"Question: {request.question}\n\n"
            "Answer:"
        )

        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=1024)
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            answer_text = response.content.strip()
        except Exception as e:
            logger.error(f"Direct RAG LLM call failed: {e}")
            raise HTTPException(status_code=500, detail=f"LLM synthesis failed: {e}")

        doc_sources = list(dict.fromkeys(s.doc_uuid for s in sources if s.doc_uuid))

        return DirectAskResponse(
            query_id=query_id,
            answer=answer_text,
            sources=sources,
            doc_sources=doc_sources,
        )

    async def _cleanup_query_data(self, query_id: str) -> None:
        """Cleanup query-specific data (background task)."""
        
        # In production, this might clean up temporary files, cache entries, etc.
        logger.debug(f"Cleaning up data for query {query_id}")
        
        # Clean up old metrics periodically
        performance_monitor.clear_old_metrics(max_age_hours=24)


# Create service instance
service = QueryReactorService()
app = service.app


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("QueryReactor API starting up...")
    
    # Initialize components
    config_loader.load_all()
    
    logger.info("QueryReactor API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("QueryReactor API shutting down...")
    
    # Cleanup tasks
    performance_monitor.clear_old_metrics(max_age_hours=0)  # Clear all metrics
    
    logger.info("QueryReactor API shutdown complete")


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    host = config_loader.get_config("api.host", "0.0.0.0")
    port = config_loader.get_config("api.port", 8000)
    workers = config_loader.get_config("api.workers", 1)
    
    # Run server
    uvicorn.run(
        "src.api.service:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        reload=False
    )