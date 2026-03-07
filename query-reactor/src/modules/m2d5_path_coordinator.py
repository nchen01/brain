"""Path Execution Coordinator - 協調多路徑並行執行"""

from typing import List, Dict, Set, Optional, Any
import asyncio
from uuid import UUID
from pydantic import BaseModel, Field

from ..models import ReactorState, WorkUnit, EvidenceItem, RoutePlan
from ..models.state import PathStats
from .base import BaseModule


class PathExecutionPlan(BaseModel):
    """路徑執行計劃"""
    path_id: str = Field(description="路徑識別碼 (P1, P2, P3)")
    assigned_workunits: List[UUID] = Field(description="分配給此路徑的 WorkUnit IDs")
    module_name: str = Field(description="執行模組名稱 (M3, M5, M6)")
    priority: int = Field(default=1, description="執行優先級")
    estimated_time_ms: Optional[int] = Field(None, description="預估執行時間")


class PathExecutionResult(BaseModel):
    """路徑執行結果"""
    path_id: str
    workunit_results: Dict[UUID, List[EvidenceItem]] = Field(description="每個 WorkUnit 的證據結果")
    execution_stats: PathStats
    success: bool = True
    error_message: Optional[str] = None


class PathExecutionCoordinator(BaseModule):
    """路徑執行協調器 - 負責協調 M3, M5, M6 的並行執行"""
    
    def __init__(self):
        super().__init__("PATH_COORD")
        # 註冊可用的路徑模組
        self.path_modules = {
            "P1": "M3",  # Simple Retrieval
            "P2": "M5",  # Internet Retrieval  
            "P3": "M6",  # Multi-hop Reasoning
        }
    
    async def execute(self, state: ReactorState) -> ReactorState:
        """實現 BaseModule 的抽象方法"""
        return await self.execute_parallel_paths(state)
    
    async def execute_parallel_paths(self, state: ReactorState) -> ReactorState:
        """並行執行多條路徑"""
        self._log_execution_start(state, "Starting parallel path execution")
        
        # 1. 分析路由計劃，創建執行計劃
        execution_plans = self._create_execution_plans(state)
        
        if not execution_plans:
            self._log_execution_end(state, "No execution plans created")
            return state
        
        # 2. 並行執行所有路徑
        execution_results = await self._execute_paths_concurrently(execution_plans, state)
        
        # 3. 整合結果到狀態中
        self._integrate_results(state, execution_results)
        
        self._log_execution_end(state, f"Completed {len(execution_results)} path executions")
        return state
    
    def _create_execution_plans(self, state: ReactorState) -> List[PathExecutionPlan]:
        """根據路由計劃創建執行計劃"""
        execution_plans = []
        path_workunit_mapping = {}  # path_id -> [workunit_ids]
        
        # 分析每個 RoutePlan，將 WorkUnits 分組到路徑
        if not hasattr(state, 'route_plans') or not state.route_plans:
            self.logger.warning("No route plans found in state")
            return []
        
        for route_plan in state.route_plans:
            workunit_id = route_plan.workunit_id
            
            for path_id in route_plan.selected_paths:
                if path_id not in path_workunit_mapping:
                    path_workunit_mapping[path_id] = []
                path_workunit_mapping[path_id].append(workunit_id)
        
        # 為每個路徑創建執行計劃
        for path_id, workunit_ids in path_workunit_mapping.items():
            if path_id in self.path_modules:
                plan = PathExecutionPlan(
                    path_id=path_id,
                    assigned_workunits=workunit_ids,
                    module_name=self.path_modules[path_id],
                    priority=self._get_path_priority(path_id)
                )
                execution_plans.append(plan)
        
        self.logger.info(f"Created {len(execution_plans)} execution plans: {[p.path_id for p in execution_plans]}")
        return execution_plans
    
    async def _execute_paths_concurrently(self, plans: List[PathExecutionPlan], 
                                        state: ReactorState) -> List[PathExecutionResult]:
        """並行執行所有路徑"""
        # 為每個路徑創建獨立的狀態副本
        tasks = []
        
        for plan in plans:
            # 創建路徑專用的狀態副本
            path_state = self._create_path_state(state, plan)
            
            # 創建執行任務
            task = asyncio.create_task(
                self._execute_single_path(plan, path_state),
                name=f"path_{plan.path_id}"
            )
            tasks.append(task)
        
        # 等待所有路徑完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果和異常
        execution_results = []
        for i, result in enumerate(results):
            plan = plans[i]
            
            if isinstance(result, Exception):
                # 處理異常
                execution_results.append(PathExecutionResult(
                    path_id=plan.path_id,
                    workunit_results={},
                    execution_stats=PathStats(
                        path_id=plan.path_id,
                        execution_time_ms=0,
                        evidence_count=0,
                        success=False,
                        error_message=str(result)
                    ),
                    success=False,
                    error_message=str(result)
                ))
            else:
                execution_results.append(result)
        
        return execution_results
    
    def _create_path_state(self, original_state: ReactorState, plan: PathExecutionPlan) -> ReactorState:
        """為特定路徑創建狀態副本"""
        # 創建狀態副本
        path_state = original_state.model_copy(deep=True)
        
        # 只保留分配給此路徑的 WorkUnits
        assigned_workunits = []
        for workunit in path_state.workunits:
            if workunit.id in plan.assigned_workunits:
                assigned_workunits.append(workunit)
        
        path_state.workunits = assigned_workunits
        
        # 添加路徑特定的元數據
        path_state.current_path_id = plan.path_id
        path_state.current_module = plan.module_name
        
        return path_state
    
    async def _execute_single_path(self, plan: PathExecutionPlan, 
                                 path_state: ReactorState) -> PathExecutionResult:
        """執行單一路徑"""
        import time
        start_time = time.time()
        
        try:
            # 根據路徑 ID 選擇對應的模組
            if plan.path_id == "P1":
                from .m3_simple_retrieval_langgraph import simple_retrieval_langgraph
                result_state = await simple_retrieval_langgraph.execute(path_state)
            elif plan.path_id == "P2":
                from .m5_internet_retrieval_langgraph import m5_internet_retrieval
                result_state = await m5_internet_retrieval.execute(path_state)
            elif plan.path_id == "P3":
                # TODO: 實現 M6 Multi-hop
                self.logger.warning(f"M6 (P3) not implemented yet") 
                result_state = path_state
            else:
                raise ValueError(f"Unknown path ID: {plan.path_id}")
            
            # Apply quality check to evidence from this path (M4 as quality gate)
            from .m4_retrieval_quality_check_langgraph import m4_quality_check
            quality_checked_state = await m4_quality_check.check_path_evidence_quality(result_state, plan.path_id)
            
            # 收集結果 (使用質量檢查後的狀態)
            workunit_results = {}
            for workunit_id in plan.assigned_workunits:
                # 收集此 WorkUnit 相關的證據 (已經過質量檢查)
                workunit_evidence = [
                    evidence for evidence in quality_checked_state.evidences 
                    if evidence.workunit_id == workunit_id
                ]
                workunit_results[workunit_id] = workunit_evidence
            
            # 創建執行統計 (包含質量檢查後的證據數量)
            execution_time = (time.time() - start_time) * 1000
            total_evidence = sum(len(evidences) for evidences in workunit_results.values())
            
            execution_stats = PathStats(
                path_id=plan.path_id,
                execution_time_ms=execution_time,
                evidence_count=total_evidence,
                success=True
            )
            
            return PathExecutionResult(
                path_id=plan.path_id,
                workunit_results=workunit_results,
                execution_stats=execution_stats,
                success=True
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            execution_stats = PathStats(
                path_id=plan.path_id,
                execution_time_ms=execution_time,
                evidence_count=0,
                success=False,
                error_message=str(e)
            )
            
            return PathExecutionResult(
                path_id=plan.path_id,
                workunit_results={},
                execution_stats=execution_stats,
                success=False,
                error_message=str(e)
            )
    
    def _integrate_results(self, state: ReactorState, results: List[PathExecutionResult]):
        """將路徑執行結果整合到主狀態中"""
        # 整合所有證據
        for result in results:
            for workunit_id, evidences in result.workunit_results.items():
                for evidence in evidences:
                    state.add_evidence(evidence)
        
        # 添加路徑統計
        for result in results:
            state.add_path_stats(result.execution_stats)
        
        # 記錄路徑執行結果
        if not hasattr(state, 'path_execution_results'):
            state.path_execution_results = []
        state.path_execution_results.extend(results)
    
    def _get_path_priority(self, path_id: str) -> int:
        """獲取路徑優先級"""
        priorities = {
            "P1": 1,  # Simple Retrieval - 最快
            "P2": 2,  # Internet Retrieval - 中等
            "P3": 3,  # Multi-hop - 最慢但最全面
        }
        return priorities.get(path_id, 1)


# 全局實例
path_coordinator = PathExecutionCoordinator()