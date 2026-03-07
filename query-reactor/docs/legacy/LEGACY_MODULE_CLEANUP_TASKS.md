# Legacy Module Cleanup Task List

## 🎯 Objective
Systematically remove old/legacy modules and tests that are no longer needed, while ensuring enhanced modules work properly. This will be done incrementally with validation at each step.

---

## 📋 **Phase 1: Pre-Cleanup Assessment and Preparation**

### **Task 1.1: Inventory and Analysis**
- [ ] 1.1.1 Create inventory of all legacy modules to be removed
- [ ] 1.1.2 Identify all related test files for legacy modules
- [ ] 1.1.3 Check dependencies and imports that reference legacy modules
- [ ] 1.1.4 Create backup validation script for enhanced modules
- [ ] 1.1.5 Document current module usage in workflow files

### **Task 1.2: Enhanced Module Validation Setup**
- [ ] 1.2.1 Create comprehensive test for enhanced modules functionality
- [ ] 1.2.2 Verify all enhanced modules can be imported correctly
- [ ] 1.2.3 Test basic execution of each enhanced module
- [ ] 1.2.4 Validate enhanced module integration points
- [ ] 1.2.5 Create rollback plan if issues are discovered

---

## 📋 **Phase 2: Update Import System and Dependencies**

### **Task 2.1: Update Module Imports**
- [ ] 2.1.1 Update `src/modules/__init__.py` to prioritize enhanced modules
- [ ] 2.1.2 Update workflow files to use enhanced modules
- [ ] 2.1.3 Update any configuration files referencing old modules
- [ ] 2.1.4 Search and update any hardcoded module references
- [ ] 2.1.5 Test import system after updates

### **Task 2.2: Workflow Integration Updates**
- [ ] 2.2.1 Update `src/workflow/graph.py` to use enhanced modules
- [ ] 2.2.2 Update any orchestration files
- [ ] 2.2.3 Update main execution files
- [ ] 2.2.4 Test workflow execution with enhanced modules
- [ ] 2.2.5 Validate end-to-end functionality

---

## 📋 **Phase 3: Incremental Legacy Module Removal**

### **Task 3.1: Remove M0 Legacy (QA Human)**
- [ ] 3.1.1 Remove `src/modules/m0_qa_human.py`
- [ ] 3.1.2 Remove `tests/modules/test_m0_qa_human.py`
- [ ] 3.1.3 Update imports to remove M0 legacy references
- [ ] 3.1.4 Test M0 enhanced module functionality
- [ ] 3.1.5 Run integration tests to ensure no breakage
- [ ] 3.1.6 Commit M0 cleanup changes

### **Task 3.2: Remove M1 Legacy (Query Preprocessor)**
- [ ] 3.2.1 Remove `src/modules/m1_query_preprocessor.py`
- [ ] 3.2.2 Remove `tests/modules/test_m1_query_preprocessor.py`
- [ ] 3.2.3 Update imports to remove M1 legacy references
- [ ] 3.2.4 Test M1 enhanced module functionality
- [ ] 3.2.5 Run integration tests to ensure no breakage
- [ ] 3.2.6 Commit M1 cleanup changes

### **Task 3.3: Remove M2 Legacy (Query Router)**
- [ ] 3.3.1 Remove `src/modules/m2_query_router.py`
- [ ] 3.3.2 Remove `tests/modules/test_m2_query_router.py`
- [ ] 3.3.3 Update imports to remove M2 legacy references
- [ ] 3.3.4 Test M2 enhanced module functionality
- [ ] 3.3.5 Run integration tests to ensure no breakage
- [ ] 3.3.6 Commit M2 cleanup changes

### **Task 3.4: Remove M3 Legacy (Simple Retrieval)**
- [ ] 3.4.1 Remove `src/modules/m3_simple_retrieval.py`
- [ ] 3.4.2 Remove `tests/modules/test_m3_simple_retrieval.py`
- [ ] 3.4.3 Update imports to remove M3 legacy references
- [ ] 3.4.4 Test M3 enhanced module functionality
- [ ] 3.4.5 Run integration tests to ensure no breakage
- [ ] 3.4.6 Commit M3 cleanup changes

### **Task 3.5: Remove M4 Legacy (Retrieval Quality Check)**
- [ ] 3.5.1 Remove `src/modules/m4_retrieval_quality_check.py`
- [ ] 3.5.2 Remove `tests/modules/test_m4_retrieval_quality_check.py`
- [ ] 3.5.3 Update imports to remove M4 legacy references
- [ ] 3.5.4 Test M4 enhanced module functionality
- [ ] 3.5.5 Run integration tests to ensure no breakage
- [ ] 3.5.6 Commit M4 cleanup changes

### **Task 3.6: Remove M5 Legacy (Internet Retrieval)**
- [ ] 3.6.1 Remove `src/modules/m5_internet_retrieval.py`
- [ ] 3.6.2 Update imports to remove M5 legacy references (no test file exists)
- [ ] 3.6.3 Test M5 enhanced module functionality
- [ ] 3.6.4 Run integration tests to ensure no breakage
- [ ] 3.6.5 Commit M5 cleanup changes

### **Task 3.7: Remove M6 Legacy (Multi-hop Orchestrator)**
- [ ] 3.7.1 Remove `src/modules/m6_multihop_orchestrator.py`
- [ ] 3.7.2 Update imports to remove M6 legacy references (no test file exists)
- [ ] 3.7.3 Test M6 enhanced module functionality
- [ ] 3.7.4 Run integration tests to ensure no breakage
- [ ] 3.7.5 Commit M6 cleanup changes

### **Task 3.8: Remove M7 Legacy (Evidence Aggregator)**
- [ ] 3.8.1 Remove `src/modules/m7_evidence_aggregator.py`
- [ ] 3.8.2 Update imports to remove M7 legacy references (no test file exists)
- [ ] 3.8.3 Test M7 enhanced module functionality
- [ ] 3.8.4 Run integration tests to ensure no breakage
- [ ] 3.8.5 Commit M7 cleanup changes

### **Task 3.9: Remove M8 Legacy (ReRanker)**
- [ ] 3.9.1 Remove `src/modules/m8_reranker.py`
- [ ] 3.9.2 Update imports to remove M8 legacy references (no test file exists)
- [ ] 3.9.3 Test M8 enhanced module functionality
- [ ] 3.9.4 Run integration tests to ensure no breakage
- [ ] 3.9.5 Commit M8 cleanup changes

### **Task 3.10: Remove M9 Legacy (Smart Retrieval Controller)**
- [ ] 3.10.1 Remove `src/modules/m9_smart_retrieval_controller.py`
- [ ] 3.10.2 Update imports to remove M9 legacy references (no test file exists)
- [ ] 3.10.3 Test M9 enhanced module functionality
- [ ] 3.10.4 Run integration tests to ensure no breakage
- [ ] 3.10.5 Commit M9 cleanup changes

### **Task 3.11: Remove M10 Legacy (Answer Creator)**
- [ ] 3.11.1 Remove `src/modules/m10_answer_creator.py`
- [ ] 3.11.2 Remove `tests/modules/test_m10_answer_creator.py`
- [ ] 3.11.3 Update imports to remove M10 legacy references
- [ ] 3.11.4 Test M10 enhanced module functionality
- [ ] 3.11.5 Run integration tests to ensure no breakage
- [ ] 3.11.6 Commit M10 cleanup changes

### **Task 3.12: Remove M11 Legacy (Answer Check)**
- [ ] 3.12.1 Remove `src/modules/m11_answer_check.py`
- [ ] 3.12.2 Update imports to remove M11 legacy references (no test file exists)
- [ ] 3.12.3 Test M11 enhanced module functionality
- [ ] 3.12.4 Run integration tests to ensure no breakage
- [ ] 3.12.5 Commit M11 cleanup changes

### **Task 3.13: Remove M12 Legacy (Interaction Answer)**
- [ ] 3.13.1 Remove `src/modules/m12_interaction_answer.py`
- [ ] 3.13.2 Update imports to remove M12 legacy references (no test file exists)
- [ ] 3.13.3 Test M12 enhanced module functionality
- [ ] 3.13.4 Run integration tests to ensure no breakage
- [ ] 3.13.5 Commit M12 cleanup changes

---

## 📋 **Phase 4: Clean Up Legacy Test Files and Development Files**

### **Task 4.1: Remove Development and Test Files**
- [ ] 4.1.1 Remove old development test files (`test_m0_*.py`, `test_m3_*.py`, etc.)
- [ ] 4.1.2 Remove demo files that use legacy modules
- [ ] 4.1.3 Remove enhancement documentation files (keep final completion docs)
- [ ] 4.1.4 Clean up any temporary or debug files
- [ ] 4.1.5 Update `.gitignore` if needed

### **Task 4.2: Update Documentation**
- [ ] 4.2.1 Update README.md to reflect enhanced modules only
- [ ] 4.2.2 Update DEVELOPMENT.md with new module structure
- [ ] 4.2.3 Update any API documentation
- [ ] 4.2.4 Create migration guide for users
- [ ] 4.2.5 Update project documentation

---

## 📋 **Phase 5: Final Validation and Optimization**

### **Task 5.1: Comprehensive Testing**
- [ ] 5.1.1 Run full enhanced module test suite
- [ ] 5.1.2 Test all integration points
- [ ] 5.1.3 Validate workflow execution end-to-end
- [ ] 5.1.4 Performance testing of enhanced modules
- [ ] 5.1.5 Memory usage validation

### **Task 5.2: Code Optimization**
- [ ] 5.2.1 Remove unused imports throughout codebase
- [ ] 5.2.2 Optimize enhanced module imports
- [ ] 5.2.3 Clean up any dead code references
- [ ] 5.2.4 Update type hints and documentation
- [ ] 5.2.5 Run code quality checks

### **Task 5.3: Final Documentation and Cleanup**
- [ ] 5.3.1 Create final cleanup report
- [ ] 5.3.2 Update project metrics and statistics
- [ ] 5.3.3 Create deployment guide for enhanced modules
- [ ] 5.3.4 Archive legacy documentation appropriately
- [ ] 5.3.5 Final commit with cleanup completion

---

## 🧪 **Testing Strategy for Each Phase**

### **Validation Steps (Run after each module removal):**
1. **Import Test**: Verify enhanced module can be imported
2. **Functionality Test**: Basic execution test of enhanced module
3. **Integration Test**: Test module works in workflow context
4. **Regression Test**: Ensure no existing functionality broken
5. **Performance Test**: Verify no performance degradation

### **Test Commands:**
```bash
# Validate enhanced modules
python validate_enhanced_modules.py

# Test specific enhanced module
python -c "from modules import {module}_lg; print('✅ {module} import successful')"

# Run integration test
python test_all_enhanced_modules.py

# Check for import errors
python -c "import src.modules; print('✅ All imports successful')"
```

---

## 📊 **Progress Tracking**

### **Module Removal Progress:**
- [ ] M0 - QA Human
- [ ] M1 - Query Preprocessor  
- [ ] M2 - Query Router
- [ ] M3 - Simple Retrieval
- [ ] M4 - Retrieval Quality Check
- [ ] M5 - Internet Retrieval
- [ ] M6 - Multi-hop Orchestrator
- [ ] M7 - Evidence Aggregator
- [ ] M8 - ReRanker
- [ ] M9 - Smart Retrieval Controller
- [ ] M10 - Answer Creator
- [ ] M11 - Answer Check
- [ ] M12 - Interaction Answer

### **Files to Remove:**
**Legacy Modules (13 files):**
- `src/modules/m0_qa_human.py`
- `src/modules/m1_query_preprocessor.py`
- `src/modules/m2_query_router.py`
- `src/modules/m3_simple_retrieval.py`
- `src/modules/m4_retrieval_quality_check.py`
- `src/modules/m5_internet_retrieval.py`
- `src/modules/m6_multihop_orchestrator.py`
- `src/modules/m7_evidence_aggregator.py`
- `src/modules/m8_reranker.py`
- `src/modules/m9_smart_retrieval_controller.py`
- `src/modules/m10_answer_creator.py`
- `src/modules/m11_answer_check.py`
- `src/modules/m12_interaction_answer.py`

**Legacy Tests (5 files):**
- `tests/modules/test_m0_qa_human.py`
- `tests/modules/test_m1_query_preprocessor.py`
- `tests/modules/test_m2_query_router.py`
- `tests/modules/test_m3_simple_retrieval.py`
- `tests/modules/test_m4_retrieval_quality_check.py`
- `tests/modules/test_m10_answer_creator.py`

**Development/Demo Files (~20 files):**
- Various `test_m0_*.py` files
- Various `test_m3_*.py` files
- Old demo files
- Enhancement documentation files

---

## 🎯 **Success Criteria**

### **Completion Criteria:**
- ✅ All 13 legacy modules removed
- ✅ All related legacy tests removed
- ✅ Enhanced modules working correctly
- ✅ No import errors or broken references
- ✅ Full integration test suite passing
- ✅ Documentation updated
- ✅ Codebase cleaned and optimized

### **Quality Gates:**
- No functionality regression
- All enhanced modules validated
- Clean import structure
- Updated documentation
- Performance maintained or improved

---

**Estimated Timeline:** 2-3 days (working incrementally)
**Risk Level:** Low (incremental approach with validation at each step)
**Rollback Plan:** Git commits at each step allow easy rollback if issues arise