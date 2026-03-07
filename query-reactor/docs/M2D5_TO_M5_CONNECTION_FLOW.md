# M2D5 路徑協調器與 M5 網路檢索的連接機制

## 🔗 **完整連接流程**

### **步驟 1: M2D5 創建執行計劃**
```python
# 在 m2d5_path_coordinator.py 第 65-85 行
def _create_execution_plans(self, state: ReactorState) -> List[PathExecutionPlan]:
    """根據路由計劃創建執行計劃"""
    execution_plans = []
    path_workunit_mapping = {}  # path_id -> [workunit_ids]
    
    # 🔑 分析每個 RoutePlan，將 WorkUnits 分組到路徑
    for route_plan in state.route_plans:
        workunit_id = route_plan.workunit_id
        
        for path_id in route_plan.selected_paths:
            if path_id not in path_workunit_mapping:
                path_workunit_mapping[path_id] = []
            path_workunit_mapping[path_id].append(workunit_id)  # ← WorkUnit ID 分配給路徑
    
    # 為 P2 路徑創建執行計劃
    if "P2" in path_workunit_mapping:
        plan = PathExecutionPlan(
            path_id="P2",
            assigned_workunits=path_workunit_mapping["P2"],  # ← 分配給 M5 的 WorkUnit IDs
            module_name="M5",
            priority=2
        )
        execution_plans.append(plan)
```

### **步驟 2: M2D5 為 M5 創建專用狀態**
```python
# 在 m2d5_path_coordinator.py 第 145-165 行
def _create_path_state(self, original_state: ReactorState, plan: PathExecutionPlan) -> ReactorState:
    """為特定路徑創建狀態副本"""
    # 🔑 創建狀態副本
    path_state = original_state.model_copy(deep=True)
    
    # 🔑 只保留分配給此路徑的 WorkUnits
    assigned_workunits = []
    for workunit in path_state.workunits:
        if workunit.id in plan.assigned_workunits:  # ← 檢查是否分配給 M5
            assigned_workunits.append(workunit)
    
    path_state.workunits = assigned_workunits  # ← M5 只會看到分配給它的 WorkUnits
    
    # 添加路徑特定的元數據
    path_state.current_path_id = plan.path_id  # "P2"
    path_state.current_module = plan.module_name  # "M5"
    
    return path_state
```

### **步驟 3: M2D5 調用 M5 模組**
```python
# 在 m2d5_path_coordinator.py 第 175-180 行
async def _execute_single_path(self, plan: PathExecutionPlan, path_state: ReactorState):
    """執行單一路徑"""
    try:
        # 🔑 根據路徑 ID 選擇對應的模組
        if plan.path_id == "P2":
            from .m5_internet_retrieval_langgraph import m5_internet_retrieval
            result_state = await m5_internet_retrieval.execute(path_state)  # ← 調用 M5
```

### **步驟 4: M5 接收並處理 WorkUnits**
```python
# 在 m5_internet_retrieval_langgraph.py 第 40-55 行
async def execute(self, state: ReactorState) -> ReactorState:
    """Execute internet retrieval for all WorkUnits in the state."""
    self._log_execution_start(state, f"Processing {len(state.workunits)} WorkUnits")
    
    try:
        # 🔑 處理每個 WorkUnit (只有分配給 M5 的)
        for workunit in state.workunits:  # ← 這些是 M2D5 篩選後的 WorkUnits
            await self._process_workunit(state, workunit)
        
        evidence_count = len([e for e in state.evidences if any(
            e.workunit_id == wu.id for wu in state.workunits
        )])
        
        self._log_execution_end(state, f"Retrieved {evidence_count} evidence items")
        return state
```

### **步驟 5: M5 處理單個 WorkUnit**
```python
# 在 m5_internet_retrieval_langgraph.py 第 65-90 行
async def _process_workunit(self, state: ReactorState, workunit) -> None:
    """Process a single WorkUnit to retrieve evidence."""
    try:
        self.logger.info(f"[{self.module_code}] Processing WorkUnit: {workunit.text[:50]}...")
        
        # 🔑 使用 WorkUnit 的文本進行 Perplexity 搜索
        if use_actual_api:
            search_results = await self._search_perplexity(workunit.text)  # ← 用 WorkUnit 文本搜索
        else:
            search_results = self._create_placeholder_search_results(workunit.text)
        
        # 🔑 創建證據項目，關聯到此 WorkUnit
        evidence_items = await self._create_evidence_items(
            search_results, workunit, state.original_query.user_id, 
            state.original_query.conversation_id
        )
        
        # 🔑 將證據添加到狀態中
        for evidence in evidence_items:
            state.add_evidence(evidence)  # ← 證據會標記 workunit_id
```

### **步驟 6: M5 創建證據項目**
```python
# 在 m5_internet_retrieval_langgraph.py 第 350-380 行
async def _create_evidence_items(self, search_results: List[Dict[str, Any]], 
                               workunit, user_id: UUID, conversation_id: UUID) -> List[EvidenceItem]:
    """Convert search results to EvidenceItem objects."""
    evidence_items = []
    
    for i, result in enumerate(search_results):
        try:
            # 🔑 創建證據項目，關聯到 WorkUnit
            evidence = EvidenceItem(
                workunit_id=workunit.id,  # ← 關鍵：關聯到處理的 WorkUnit
                user_id=user_id,
                conversation_id=conversation_id,
                content=content,
                title=title,
                score_raw=0.8 - (i * 0.1),
                provenance=provenance
            )
            
            evidence_items.append(evidence)
```

### **步驟 7: M2D5 收集結果**
```python
# 在 m2d5_path_coordinator.py 第 185-200 行
# 收集結果 (使用質量檢查後的狀態)
workunit_results = {}
for workunit_id in plan.assigned_workunits:  # ← 遍歷分配給 M5 的 WorkUnit IDs
    # 🔑 收集此 WorkUnit 相關的證據
    workunit_evidence = [
        evidence for evidence in quality_checked_state.evidences 
        if evidence.workunit_id == workunit_id  # ← 根據 workunit_id 過濾證據
    ]
    workunit_results[workunit_id] = workunit_evidence  # ← 按 WorkUnit 分組證據

return PathExecutionResult(
    path_id=plan.path_id,
    workunit_results=workunit_results,  # ← 返回按 WorkUnit 分組的結果
    execution_stats=execution_stats,
    success=True
)
```

## 🔍 **實際執行示例**

假設 M2 路由器創建了以下路由計劃：

```
RoutePlan 1: {
    workunit_id: "wu-123",
    selected_paths: ["P1", "P2"]  // WorkUnit 123 分配給 P1 和 P2
}

RoutePlan 2: {
    workunit_id: "wu-456", 
    selected_paths: ["P2"]  // WorkUnit 456 只分配給 P2
}

RoutePlan 3: {
    workunit_id: "wu-789",
    selected_paths: ["P1", "P3"]  // WorkUnit 789 分配給 P1 和 P3
}
```

**M2D5 為 P2 (M5) 創建執行計劃：**
```
ExecutionPlan P2: {
    path_id: "P2",
    assigned_workunits: ["wu-123", "wu-456"],  // 只有這兩個 WorkUnits 分配給 M5
    module_name: "M5"
}
```

**M2D5 為 M5 創建專用狀態：**
```python
path_state.workunits = [
    WorkUnit(id="wu-123", text="Latest AI developments"),
    WorkUnit(id="wu-456", text="AI comparison 2023 vs 2024")
]
# WorkUnit wu-789 不在這個狀態中，因為它沒有分配給 P2
```

**M5 處理過程：**
```python
# M5 只會看到分配給它的 WorkUnits
for workunit in state.workunits:  # 只有 wu-123 和 wu-456
    # 為 wu-123 搜索 "Latest AI developments"
    # 為 wu-456 搜索 "AI comparison 2023 vs 2024"
    search_results = await self._search_perplexity(workunit.text)
    
    # 創建證據，標記 workunit_id
    evidence = EvidenceItem(
        workunit_id=workunit.id,  # wu-123 或 wu-456
        content=search_content,
        # ...
    )
```

**M2D5 收集結果：**
```python
workunit_results = {
    "wu-123": [evidence1, evidence2, evidence3],  # M5 為 wu-123 找到的證據
    "wu-456": [evidence4, evidence5]              # M5 為 wu-456 找到的證據
}
```

## 🎯 **關鍵連接點總結**

1. **WorkUnit ID 追蹤**：從 M2 路由 → M2D5 分配 → M5 處理 → 證據關聯，始終保持 WorkUnit ID 的一致性

2. **狀態過濾**：M2D5 為每個路徑創建專用狀態，確保 M5 只看到分配給它的 WorkUnits

3. **證據關聯**：M5 創建的每個證據都會標記 `workunit_id`，確保結果可以追溯到原始小問題

4. **結果分組**：M2D5 按 WorkUnit ID 收集和分組證據，便於後續處理

5. **並行安全**：每個路徑都有獨立的狀態副本，避免並行執行時的數據競爭

這樣的設計確保了 **WorkUnits 從 M2 路由決策到 M5 實際處理的完整追蹤鏈**，每個小問題都能得到對應的搜索結果和證據。