# System Setup Instructions for QueryReactor

## 🔧 **CRITICAL: Virtual Environment Activation**

**⚠️ IMPORTANT: Always activate the virtual environment before running any Python commands!**

### **For PowerShell (Windows):**
```powershell
# Run this command before any Python operations:
.\activate_venv.ps1
```

### **Manual Activation (if script fails):**
```powershell
# Activate virtual environment manually:
.\.venv\Scripts\Activate.ps1

# Verify activation (should show virtual environment path):
echo $env:VIRTUAL_ENV
```

### **For Bash/Linux/Mac:**
```bash
# Activate virtual environment:
source .venv/bin/activate

# Verify activation:
echo $VIRTUAL_ENV
```

---

## 📋 **Pre-Command Checklist**

Before running any Python commands, ensure:

1. ✅ **Virtual environment is activated** 
   - PowerShell: `.\activate_venv.ps1`
   - Manual: `.\.venv\Scripts\Activate.ps1`

2. ✅ **Required packages are installed**
   - pydantic (for data validation)
   - langgraph (for AI agent orchestration)
   - openai (for LLM integration)

3. ✅ **Working directory is project root**
   - Should see: `.venv/`, `src/`, `tests/`, etc.

---

## 🧪 **Testing Commands (After Activation)**

```powershell
# Test enhanced modules validation:
python validate_enhanced_modules.py

# Test enhanced module imports:
python -c "
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from modules import qa_with_human_lg, query_preprocessor_lg
print('✅ Enhanced modules imported successfully!')
"

# Run cleanup inventory:
python cleanup_inventory.py
```

---

## 🚨 **Common Issues & Solutions**

### **Issue: "No module named 'pydantic'"**
**Solution:** Virtual environment not activated
```powershell
.\activate_venv.ps1
```

### **Issue: "ImportError: attempted relative import beyond top-level package"**
**Solution:** Run from project root with proper path setup
```powershell
# Ensure you're in project root
cd D:\Github\QueryReactor
.\activate_venv.ps1
```

### **Issue: PowerShell execution policy**
**Solution:** Allow script execution
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📁 **Project Structure Reference**

```
QueryReactor/
├── .venv/                          # Virtual environment
├── src/
│   ├── modules/
│   │   ├── *_langgraph.py         # Enhanced modules (keep)
│   │   └── m*.py                  # Legacy modules (remove)
│   └── ...
├── tests/
├── activate_venv.ps1              # Activation script
└── validate_enhanced_modules.py   # Validation tool
```

---

## 🎯 **Quick Start Workflow**

1. **Activate environment:**
   ```powershell
   .\activate_venv.ps1
   ```

2. **Validate enhanced modules:**
   ```powershell
   python validate_enhanced_modules.py
   ```

3. **Run cleanup tasks:**
   ```powershell
   python cleanup_inventory.py
   ```

4. **Test specific functionality:**
   ```powershell
   python -c "from modules import simple_retrieval_lg; print('✅ Works!')"
   ```

---

**Remember: Always run `.\activate_venv.ps1` first!** 🔧