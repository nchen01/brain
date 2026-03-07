# QueryReactor 執行流程詳解

## 🔄 完整執行流程

### 階段 1: 查詢預處理
```
用戶查詢: "What are the latest AI developments and how do they compare to last year?"
    ↓
M0 (澄清): 確認查詢意圖
    ↓
M1 (查詢預處理): 拆分成多個 WorkUnits
    ↓
WorkUnits 創建:
- WorkUnit 1: "Latest AI developments 2024"
- WorkUnit 2: "AI developments comparison 2023 vs 2024"  
- WorkUnit 3: "Recent AI breakthroughs and innovations"
```

### 階段 2: 路由決策
```
M2 (查詢路由器) 分析每個 WorkUnit:

WorkUnit 1 → RoutePlan {
    workunit_id: wu1_id,
    selected_paths: ["P1", "P2"]  // 簡單檢索 + 網路檢索
}

WorkUnit 2 → RoutePlan {
    workunit_id: wu2_id, 
    selected_paths: ["P2", "P3"]  // 網路檢索 + 多跳推理
}

WorkUnit 3 → RoutePlan {
    workunit_id: wu3_id,
    selected_paths: ["P1", "P2"]  // 簡單檢索 + 網路檢索
}
```

### 階段 3: 並行執行 (關鍵！)
```
路徑協調器 (M2D5) 創建執行計劃:

ExecutionPlan P1 {
    path_id: "P1",
    assigned_workunits: [wu1_id, wu3_id],  // 2個WorkUnits分配給P1
    module_name: "M3"
}

ExecutionPlan P2 {
    path_id: "P2", 
    assigned_workunits: [wu1_id, wu2_id, wu3_id],  // 3個WorkUnits分配給P2
    module_name: "M5"
}

ExecutionPlan P3 {
    path_id: "P3",
    assigned_workunits: [wu2_id],  // 1個WorkUnit分配給P3
    module_name: "M6"
}
```

### 階段 4: 並行檢索執行
```
並行執行 (使用 asyncio.gather):

Task 1: M3 處理 [wu1_id, wu3_id]
    ├─ 為 wu1 檢索內部文檔
    └─ 為 wu3 檢索內部文檔

Task 2: M5 處理 [wu1_id, wu2_id, wu3_id]  ← 你的 Perplexity API
    ├─ 為 wu1 搜索網路資訊
    ├─ 為 wu2 搜索網路資訊  
    └─ 為 wu3 搜索網路資訊

Task 3: M6 處理 [wu2_id]
    └─ 為 wu2 進行多跳推理

每個任務完成後 → M4 質量檢查 → 過濾低質量證據
```

## 🎯 確保每個小問題都被處理的機制

### 1. **WorkUnit 追蹤機制**
```python
# 在 ReactorState 中追蹤所有 WorkUnits
class ReactorState:
    workunits: List[WorkUnit] = []  # 所有小問題
    evidences: List[EvidenceItem] = []  # 所有證據
    
    def get_evidence_for_workunit(self, workunit_id: UUID) -> List[EvidenceItem]:
        """獲取特定 WorkUnit 的所有證據"""
        return [e for e in self.evidences if e.workunit_id == workunit_id]
```

### 2. **路徑協調器的分配邏輯**
```python
def _create_path_state(self, original_state: ReactorState, plan: PathExecutionPlan):
    """為每個路徑創建專用狀態副本"""
    path_state = original_state.model_copy(deep=True)
    
    # 只保留分配給此路徑的 WorkUnits
    assigned_workunits = []
    for workunit in path_state.workunits:
        if workunit.id in plan.assigned_workunits:  # 確保只處理分配的WorkUnits
            assigned_workunits.append(workunit)
    
    path_state.workunits = assigned_workunits
    return path_state
```

### 3. **結果整合機制**
```python
def _integrate_results(self, state: ReactorState, results: List[PathExecutionResult]):
    """整合所有路徑的結果"""
    for result in results:
        for workunit_id, evidences in result.workunit_results.items():
            for evidence in evidences:
                evidence.workunit_id = workunit_id  # 確保證據與WorkUnit關聯
                state.add_evidence(evidence)
```

### 4. **證據聚合驗證**
```python
# M7 證據聚合器會驗證每個 WorkUnit 都有證據
for workunit in state.workunits:
    workunit_evidence = state.get_evidence_for_workunit(workunit.id)
    if not workunit_evidence:
        logger.warning(f"No evidence found for WorkUnit: {workunit.text}")
        # 可以觸發補救措施
```

## 🔍 實際執行示例

假設 M1 創建了 3 個 WorkUnits：

```
WorkUnit A: "Latest AI developments"
WorkUnit B: "AI comparison 2023 vs 2024"  
WorkUnit C: "Recent AI breakthroughs"
```

**路由決策：**
- A → P1, P2 (簡單檢索 + 網路檢索)
- B → P2, P3 (網路檢索 + 多跳推理)
- C → P1, P2 (簡單檢索 + 網路檢索)

**並行執行：**
```
P1 (M3) 同時處理: [A, C]
P2 (M5) 同時處理: [A, B, C]  ← 你的 Perplexity API 會為每個WorkUnit搜索
P3 (M6) 處理: [B]
```

**結果收集：**
```
WorkUnit A 獲得證據來源: P1 + P2 = 內部文檔 + 網路搜索
WorkUnit B 獲得證據來源: P2 + P3 = 網路搜索 + 多跳推理  
WorkUnit C 獲得證據來源: P1 + P2 = 內部文檔 + 網路搜索
```

## 🛡️ 容錯機制

### 1. **路徑失敗處理**
```python
if isinstance(result, Exception):
    # 路徑失敗，但其他路徑可能成功
    execution_results.append(PathExecutionResult(
        path_id=plan.path_id,
        success=False,
        error_message=str(result)
    ))
```

### 2. **WorkUnit 覆蓋檢查**
```python
# M7 會檢查每個 WorkUnit 是否有足夠的證據
for workunit in state.workunits:
    evidence_count = len(state.get_evidence_for_workunit(workunit.id))
    if evidence_count == 0:
        # 觸發補救措施或標記為未解決
        logger.warning(f"WorkUnit {workunit.id} has no evidence")
```

### 3. **質量保證**
```python
# M4 質量檢查確保每個證據都有質量評分
for evidence in evidences:
    if evidence.score_raw < quality_threshold:
        # 過濾低質量證據，但保留高質量的
        continue
```

## 📊 監控和追蹤

系統提供完整的追蹤機制：

```python
# 每個 WorkUnit 的處理狀態
workunit_status = {
    workunit.id: {
        "text": workunit.text,
        "assigned_paths": [路徑列表],
        "evidence_count": len(state.get_evidence_for_workunit(workunit.id)),
        "processing_time": execution_time,
        "success": True/False
    }
    for workunit in state.workunits
}
```

這樣的設計確保：
1. ✅ **每個小問題都被分配到至少一個檢索路徑**
2. ✅ **並行處理提高效率**
3. ✅ **容錯機制處理部分失敗**
4. ✅ **質量檢查確保證據品質**
5. ✅ **完整的追蹤和監控**