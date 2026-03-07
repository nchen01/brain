# GitHub Workflow Guide - Upload Changes and Create PR

## 🚀 **Complete GitHub Workflow**

### **Step 1: Initialize Git Repository (First Time Only)**

```bash
# Navigate to your project directory
cd D:\Github\QueryReactor

# Initialize git repository (if not already done)
git init

# Add the remote repository
git remote add origin https://github.com/SimonAlethora/QueryReactor.git

# Check if remote is added correctly
git remote -v
```

### **Step 2: Check Current Status**

```bash
# See what files have been changed
git status

# See detailed changes in files
git diff
```

### **Step 3: Stage Your Changes**

```bash
# Add specific files
git add src/modules/m5_internet_retrieval_langgraph.py
git add config.md
git add docs/M2D5_TO_M5_CONNECTION_FLOW.md
git add docs/QUERYREACTOR_FLOW_EXPLANATION.md
git add docs/P2_M5_M4_DATA_FLOW.md

# Or add all changed files at once
git add .

# Check what's staged
git status
```

### **Step 4: Commit Your Changes**

```bash
# Commit with a descriptive message
git commit -m "feat: Implement Perplexity API integration for M5 module

- Update M5 to use Perplexity 'sonar' model instead of Google Search
- Fix API response parsing for Perplexity citation structure
- Add comprehensive documentation for M2D5-M5 connection flow
- Add data flow documentation for P2→M5→M4 pipeline
- Update configuration with correct Perplexity model name"
```

### **Step 5: Create and Switch to Feature Branch**

```bash
# Create a new branch for your feature
git checkout -b feature/perplexity-integration

# Or if you want to work on main branch directly
git checkout main
```

### **Step 6: Push to GitHub**

```bash
# Push to your feature branch (recommended)
git push -u origin feature/perplexity-integration

# Or push to main branch
git push -u origin main
```

### **Step 7: Create Pull Request on GitHub**

1. **Go to your GitHub repository**: https://github.com/SimonAlethora/QueryReactor

2. **You'll see a banner** saying "Compare & pull request" - click it

3. **Fill out the PR form**:
   - **Title**: `feat: Implement Perplexity API integration for M5 module`
   - **Description**:
   ```markdown
   ## 🚀 Changes Made
   
   ### M5 Internet Retrieval Module Enhancement
   - ✅ Integrated Perplexity API for real-time web search
   - ✅ Updated model from `llama-3.1-sonar-small-128k-online` to `sonar`
   - ✅ Fixed API response parsing for Perplexity citation structure
   - ✅ Added proper error handling and fallback mechanisms
   
   ### Documentation Added
   - ✅ `docs/M2D5_TO_M5_CONNECTION_FLOW.md` - Detailed connection flow between path coordinator and M5
   - ✅ `docs/QUERYREACTOR_FLOW_EXPLANATION.md` - Complete system execution flow
   - ✅ `docs/P2_M5_M4_DATA_FLOW.md` - Data types and flow through P2→M5→M4 pipeline
   
   ### Configuration Updates
   - ✅ Updated `config.md` with correct Perplexity model name
   - ✅ Verified API key configuration in `.env`
   
   ## 🧪 Testing
   - ✅ Tested with real Perplexity API calls
   - ✅ Verified evidence creation and WorkUnit association
   - ✅ Confirmed integration with M4 quality check
   
   ## 📊 Results
   - Successfully retrieves 7 evidence items from real web sources
   - Proper citation parsing and content extraction
   - Full integration with existing QueryReactor workflow
   ```

4. **Select reviewers** (if you have collaborators)

5. **Click "Create pull request"**

## 🔧 **Alternative: Direct Push to Main (Simpler)**

If you're the only contributor and want to push directly:

```bash
# Make sure you're on main branch
git checkout main

# Add all changes
git add .

# Commit changes
git commit -m "feat: Implement Perplexity API integration for M5 module"

# Push directly to main
git push origin main
```

## 📝 **Useful Git Commands**

### **Check Status and History**
```bash
# See current status
git status

# See commit history
git log --oneline

# See changes in a file
git diff filename.py

# See staged changes
git diff --cached
```

### **Branch Management**
```bash
# List all branches
git branch -a

# Create new branch
git checkout -b feature/new-feature

# Switch branches
git checkout main
git checkout feature/perplexity-integration

# Delete branch (after merging)
git branch -d feature/perplexity-integration
```

### **Undo Changes**
```bash
# Unstage a file
git reset filename.py

# Undo changes to a file (before commit)
git checkout -- filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

## 🎯 **Recommended Workflow for Your Changes**

Since you've made significant improvements to the M5 module, here's what I recommend:

### **Option 1: Feature Branch (Best Practice)**
```bash
# 1. Create feature branch
git checkout -b feature/perplexity-integration

# 2. Add your changes
git add .

# 3. Commit with descriptive message
git commit -m "feat: Implement Perplexity API integration for M5 module

- Update M5 to use Perplexity 'sonar' model
- Fix API response parsing for citations
- Add comprehensive documentation
- Update configuration files"

# 4. Push feature branch
git push -u origin feature/perplexity-integration

# 5. Create PR on GitHub web interface
```

### **Option 2: Direct to Main (Simpler)**
```bash
# 1. Make sure you're on main
git checkout main

# 2. Add all changes
git add .

# 3. Commit
git commit -m "feat: Implement Perplexity API integration for M5 module"

# 4. Push to main
git push origin main
```

## 🔍 **Files You Should Include in Your Commit**

Based on our work, these files should be committed:

```bash
# Core module changes
git add src/modules/m5_internet_retrieval_langgraph.py

# Configuration updates
git add config.md

# New documentation
git add docs/M2D5_TO_M5_CONNECTION_FLOW.md
git add docs/QUERYREACTOR_FLOW_EXPLANATION.md
git add docs/P2_M5_M4_DATA_FLOW.md
git add docs/GITHUB_WORKFLOW_GUIDE.md

# Test files (optional)
git add test_m5_demo.py
git add test_perplexity_models.py
git add test_perplexity_response.py
```

## 🎉 **After Your PR is Created**

1. **Monitor the PR** for any feedback or review comments
2. **Make additional commits** to the same branch if changes are requested
3. **Merge the PR** when ready (or it will be merged by maintainers)
4. **Delete the feature branch** after merging (optional cleanup)

## 🚨 **Common Issues and Solutions**

### **Authentication Issues**
```bash
# If you get authentication errors, you might need to:
# 1. Use personal access token instead of password
# 2. Configure Git credentials
git config --global user.name "SimonAlethora"
git config --global user.email "your-email@example.com"
```

### **Merge Conflicts**
```bash
# If there are conflicts when pulling/merging:
git pull origin main
# Resolve conflicts in files
git add .
git commit -m "resolve merge conflicts"
```

### **Large Files**
```bash
# If you have large files, you might need Git LFS
git lfs track "*.model"
git add .gitattributes
```

Choose the workflow that feels most comfortable for you. The feature branch approach is more professional, but direct push to main is simpler for solo projects!