"""Main entry point for QueryReactor application."""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.logging.setup import setup_logging
from src.config.loader import config_loader


async def main():
    """Main application entry point."""
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config_loader.load_all()
    
    print("QueryReactor v1.0.0")
    print("===================")
    print()
    print("Available commands:")
    print("  python main.py server    - Start the API server")
    print("  python main.py test      - Run a test query")
    print("  python main.py config    - Show configuration")
    print("  python main.py health    - Check system health")
    print()
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Please specify a command. Use 'python main.py' to see available commands.")
        return
    
    command = sys.argv[1].lower()
    
    if command == "server":
        await start_server()
    elif command == "test":
        await run_test_query()
    elif command == "config":
        show_configuration()
    elif command == "health":
        await check_health()
    else:
        print(f"Unknown command: {command}")
        print("Use 'python main.py' to see available commands.")


async def start_server():
    """Start the API server."""
    import uvicorn
    from src.api.service import app
    
    # Get server configuration
    host = config_loader.get_config("api.host", "0.0.0.0")
    port = config_loader.get_config("api.port", 8000)
    
    print(f"Starting QueryReactor API server on {host}:{port}")
    print("Press Ctrl+C to stop the server")
    print()
    
    # Run server
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        reload=False
    )
    
    server = uvicorn.Server(config)
    await server.serve()


async def run_test_query():
    """Run a test query through the system."""
    from uuid import uuid4
    from src.models import UserQuery
    from src.workflow.graph import query_reactor_graph
    
    print("Running test query...")
    
    # Create test query
    test_query = UserQuery(
        user_id=uuid4(),
        conversation_id=uuid4(),
        text="What is Python programming language?"
    )
    
    print(f"Query: {test_query.text}")
    print("Processing...")
    
    try:
        # Process query
        result = await query_reactor_graph.process_query(
            query_data=test_query.dict(),
            config=config_loader.config
        )
        
        if result.final_answer:
            print("\nAnswer:")
            print(result.final_answer.text)
            print(f"\nConfidence: {result.final_answer.confidence:.2f}")
            print(f"Citations: {len(result.final_answer.citations)}")
            
            if result.final_answer.limitations:
                print("\nLimitations:")
                for limitation in result.final_answer.limitations:
                    print(f"  - {limitation}")
        else:
            print("No answer generated")
        
        print(f"\nProcessing completed successfully!")
        print(f"WorkUnits processed: {len(result.workunits)}")
        print(f"Evidence items: {len(result.evidences)}")
        
    except Exception as e:
        print(f"Error processing query: {e}")
        import traceback
        traceback.print_exc()


def show_configuration():
    """Show current configuration."""
    print("Current Configuration:")
    print("=====================")
    
    # Show key configuration values
    config_items = [
        ("API Host", config_loader.get_config("api.host", "0.0.0.0")),
        ("API Port", config_loader.get_config("api.port", 8000)),
        ("Answer Creator Model", config_loader.get_config("ac.model", "gpt-4")),
        ("Min Confidence", config_loader.get_config("smr.min_confidence", 0.7)),
        ("Max Loops (SMR->QP)", config_loader.get_config("loop.max.smartretrieval_to_qp", 2)),
        ("Max Loops (ACK->AC)", config_loader.get_config("loop.max.answercheck_to_ac", 3)),
        ("Enable Decomposition", config_loader.get_config("qp.enable_decomposition", True)),
        ("Allow Partial Answers", config_loader.get_config("ac.allow_partial_answer", True)),
        ("Log Level", config_loader.get_env("LOG_LEVEL", "INFO")),
    ]
    
    for name, value in config_items:
        print(f"  {name:25}: {value}")
    
    print()
    print("Environment Variables:")
    print("=====================")
    
    env_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", 
        "LOG_LEVEL",
        "OTEL_SERVICE_NAME",
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    ]
    
    for var in env_vars:
        value = config_loader.get_env(var)
        if value:
            # Mask sensitive values
            if "key" in var.lower() or "token" in var.lower():
                masked_value = value[:8] + "..." if len(value) > 8 else "***"
                print(f"  {var:30}: {masked_value}")
            else:
                print(f"  {var:30}: {value}")
        else:
            print(f"  {var:30}: (not set)")


async def check_health():
    """Check system health."""
    print("QueryReactor Health Check")
    print("========================")
    
    # Check configuration
    try:
        config_loader.load_all()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return
    
    # Check workflow initialization
    try:
        from src.workflow.graph import query_reactor_graph
        if query_reactor_graph.graph:
            print("✓ Workflow graph initialized")
        else:
            print("✗ Workflow graph not initialized")
    except Exception as e:
        print(f"✗ Workflow error: {e}")
    
    # Check modules
    try:
        from src.modules import (
            qa_with_human_module, query_preprocessor_module, query_router_module,
            simple_retrieval_module, internet_retrieval_module, multihop_orchestrator_module,
            evidence_aggregator_module, reranker_module, smart_retrieval_controller_module,
            answer_creator_module, answer_check_module, interaction_answer_module
        )
        print("✓ All modules imported successfully")
    except Exception as e:
        print(f"✗ Module import error: {e}")
    
    # Check data models
    try:
        from src.models import UserQuery, ReactorState, EvidenceItem, Answer
        print("✓ Data models imported successfully")
    except Exception as e:
        print(f"✗ Data model error: {e}")
    
    # Check observability
    try:
        from src.observability.tracing import tracing_manager
        from src.observability.metrics import performance_monitor
        
        if tracing_manager.is_enabled():
            print("✓ OpenTelemetry tracing enabled")
        else:
            print("⚠ OpenTelemetry tracing disabled")
        
        if performance_monitor.enabled:
            print("✓ Performance monitoring enabled")
        else:
            print("⚠ Performance monitoring disabled")
            
    except Exception as e:
        print(f"✗ Observability error: {e}")
    
    print("\nHealth check completed!")


if __name__ == "__main__":
    asyncio.run(main())