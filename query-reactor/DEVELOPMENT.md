# QueryReactor Development Guide

## Debugging and Monitoring with LangGraph Tools

Since QueryReactor is built with LangGraph, you have access to powerful native debugging tools that are specifically designed for graph-based workflows.

## 🔍 **LangSmith - Production Monitoring**

LangSmith is the recommended way to monitor QueryReactor in production and development.

### **Setup LangSmith**

1. **Get LangSmith API Key**:
   - Sign up at [smith.langchain.com](https://smith.langchain.com)
   - Create a new project called "queryreactor"
   - Get your API key

2. **Configure Environment**:
   ```bash
   # In your .env file
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_actual_langsmith_api_key
   LANGCHAIN_PROJECT=queryreactor
   ```

3. **Run QueryReactor**:
   ```bash
   python main.py server
   ```

### **What You'll See in LangSmith**

**🔄 Complete Workflow Traces**:
```
QueryReactor Execution Trace:
├── M0: qa_with_human (45ms)
│   ├── Input: UserQuery("What is Python?")
│   └── Output: ClarifiedQuery(confidence=0.9)
├── M1: query_preprocessor (120ms)
│   ├── Input: ClarifiedQuery
│   └── Output: [WorkUnit("What is Python?")]
├── M2: query_router (30ms)
│   ├── Input: [WorkUnit]
│   └── Output: RoutePlan(paths=["P1", "P2"])
├── M3: simple_retrieval (200ms) [Parallel]
│   └── Output: 3 EvidenceItems
├── M5: internet_retrieval (180ms) [Parallel]
│   └── Output: 2 EvidenceItems
├── M7: evidence_aggregator (50ms)
│   └── Output: 4 EvidenceItems (1 duplicate removed)
├── M8: reranker (75ms)
│   └── Output: RankedEvidence (top_k=3)
├── M9: smart_retrieval_controller (25ms)
│   └── Decision: answer_ready
├── M10: answer_creator (300ms)
│   └── Output: Answer with 3 citations
├── M11: answer_check (100ms)
│   └── Verification: passed
└── M12: interaction_answer (20ms)
    └── Final Response delivered
```

**📊 Key Metrics You Can Track**:
- **Module Performance**: Which modules are slowest?
- **Loop Behavior**: How often do refinement loops occur?
- **Evidence Quality**: How much evidence is filtered out?
- **Path Usage**: Which retrieval paths are most effective?
- **Error Patterns**: Where do failures typically occur?

## 🎨 **LangGraph Studio - Interactive Development**

Perfect for development and debugging individual queries.

### **Setup LangGraph Studio**

1. **Install LangGraph CLI**:
   ```bash
   uv add --dev langgraph-cli
   ```

2. **Start LangGraph Studio**:
   ```bash
   langgraph dev
   ```

3. **Access Studio**:
   - Open http://localhost:8123
   - Select "QueryReactor Workflow"

### **What You Can Do in Studio**

**🎯 Interactive Debugging**:
- **Step through execution**: Pause at any module
- **Inspect state**: See ReactorState at each step
- **Modify inputs**: Test different queries
- **Visualize flow**: See the graph execution in real-time

**🔧 Development Workflow**:
```bash
# 1. Start Studio
langgraph dev

# 2. Open browser to http://localhost:8123

# 3. Test queries interactively:
#    - Input: "What is Python programming?"
#    - Watch each module execute
#    - Inspect evidence at each step
#    - See loop decisions in real-time

# 4. Debug issues:
#    - Set breakpoints at specific modules
#    - Examine state transformations
#    - Test edge cases
```

## 📈 **Monitoring Dashboard Comparison**

### **LangSmith Dashboard**:
- **Workflow Traces**: Complete execution paths
- **Performance Analytics**: Module timing analysis
- **Error Tracking**: Failed executions with context
- **Cost Tracking**: Token usage and API costs
- **A/B Testing**: Compare different prompt versions

### **LangGraph Studio**:
- **Real-time Debugging**: Step-by-step execution
- **State Inspection**: ReactorState at each node
- **Interactive Testing**: Modify inputs and re-run
- **Graph Visualization**: Visual workflow representation

### **OpenTelemetry/Jaeger** (Still useful for):
- **Infrastructure Monitoring**: Server performance, memory usage
- **Cross-Service Tracing**: If QueryReactor calls other services
- **Custom Metrics**: Business-specific measurements

## 🚀 **Recommended Development Setup**

### **For Local Development**:
```bash
# 1. Enable LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=queryreactor-dev

# 2. Start LangGraph Studio
langgraph dev

# 3. Run QueryReactor
python main.py server

# 4. Test queries and watch in Studio
```

### **For Production**:
```bash
# Enable LangSmith for production monitoring
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=queryreactor-prod
```

## 🔧 **Debugging Common Issues**

### **Query Not Processing**:
1. Check LangSmith trace to see where it stops
2. Look at module inputs/outputs
3. Check loop counters and limits

### **Poor Answer Quality**:
1. Examine evidence retrieval in each path (M3, M5, M6)
2. Check reranking scores (M8)
3. Review answer verification results (M11)

### **Performance Issues**:
1. LangSmith shows module timing
2. Identify bottleneck modules
3. Check if loops are occurring too frequently

### **Loop Issues**:
1. LangSmith traces show loop iterations
2. Check loop counter limits in config.md
3. Review SmartRetrieval Controller decisions (M9)

## 💡 **Pro Tips**

1. **Use LangSmith Projects**: Separate dev/staging/prod environments
2. **Tag Executions**: Add metadata for easier filtering
3. **Monitor Costs**: LangSmith tracks token usage
4. **Set Alerts**: Get notified of high error rates
5. **Compare Versions**: A/B test different configurations

This approach gives you much better visibility into your QueryReactor workflow than generic observability tools!