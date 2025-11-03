# Dependency Upgrade Example

This example demonstrates how Alphanso automates the process of upgrading Python dependencies that have breaking API changes.

## The Problem

When upgrading a dependency to a new major version, you often face:

- Import path changes (modules moved)
- Renamed classes and functions
- Changed constructor signatures (new required parameters)
- Renamed methods
- Different return types (dict → object)
- Changed data access patterns

**Manual Process** (tedious):
1. Upgrade dependency
2. Run tests → see failures
3. Read error messages
4. Consult documentation/changelog
5. Update imports in source code
6. Update API calls
7. Update tests
8. Re-run tests
9. Repeat steps 2-8 until all pass

This takes 30+ minutes and is error-prone.

## The Solution

Alphanso automates this with AI:

1. **Pre-action**: Upgrades dependency
2. **Validators**: Detect failures (import, syntax, tests)
3. **AI Fix**: Claude investigates errors and fixes code
4. **Re-validate**: Framework re-runs validators
5. **Iterate**: Continues until all validators pass

**Result**: Automated in ~5 minutes with full test coverage.

## What This Example Does

### The Scenario

**analytics v1.0 API** (original):
```python
from analytics import DataProcessor

processor = DataProcessor()
result = processor.analyze(data)
print(result['mean'])  # Dict access
```

**analytics v2.0 API** (breaking changes):
```python
from analytics.core import Analyzer  # Module moved

analyzer = Analyzer(config={'mode': 'fast'})  # Requires config
result = analyzer.process(data)  # Method renamed
print(result.statistics.mean)  # Object access
```

### Breaking Changes (6 total)

1. **Module moved**: `analytics` → `analytics.core`
2. **Class renamed**: `DataProcessor` → `Analyzer`
3. **Constructor requires parameter**: `Analyzer(config={'mode': 'fast'})`
4. **Method renamed**: `.analyze()` → `.process()`
5. **Return type changed**: `dict` → `AnalysisResult` object
6. **Data access changed**: `result['key']` → `result.statistics.key`

### AI Convergence Flow

**Attempt 1: Detect Failures**
```
NODE: pre_actions
[1/1] Upgrade analytics package to v2.0 → ✅ Success

NODE: validate
[1/3] Import Check → ❌ Failed
  ImportError: cannot import name 'DataProcessor' from 'analytics'
[2/3] Syntax Check → ✅ Success
[3/3] Unit Tests → ❌ Failed (skipped due to import failure)

NODE: decide
❌ Validation failed (attempt 1/5)
Decision: RETRY
```

**Attempt 2: AI Fixes Issues**
```
NODE: ai_fix
Invoking Claude Agent SDK to investigate and fix failures...

💭 Claude investigates:
   🔧 Bash: source venv/bin/activate && python -c 'from src.main import main'
   📖 Read: src/main.py
   📖 Read: analytics-v2/analytics/core/__init__.py
   💭 Thinking: The import path changed and class was renamed...

💭 Claude fixes:
   ✏️ Edit: src/main.py (update imports, class name, constructor, method call, data access)
   ✏️ Edit: tests/test_main.py (update assertions)

✅ Claude used 6 SDK tools

NODE: validate
[1/3] Import Check → ✅ Success
[2/3] Syntax Check → ✅ Success
[3/3] Unit Tests → ✅ Success

NODE: decide
✅ All validators PASSED
Decision: END with success
```

**Result**: ✅ Completed in 2 attempts (~2-3 minutes)

## How to Run

### Quick Start
```bash
./run.sh
```

### Step-by-Step
```bash
# 1. Create project with v1.0 dependency
./setup.sh

# 2. Manually inspect before upgrade
cd my-project
source venv/bin/activate
pytest tests/ -v  # All pass with v1.0

# 3. Run convergence (upgrades to v2.0 and fixes)
cd ..
uv run alphanso run --config config.yaml

# 4. Verify fixes
cd my-project
source venv/bin/activate
pytest tests/ -v  # All pass with v2.0!
```

## Requirements

- Python 3.11+
- Alphanso installed (`pip install -e /path/to/alphanso`)
- `ANTHROPIC_API_KEY` environment variable set
- `uv` installed (or use `python -m alphanso` instead)

## Verifying the Upgrade Succeeded

After running `./run.sh`, here's how to verify Claude successfully upgraded your code from v1.0 to v2.0:

### 1. Check What Files Changed

Claude modified these files:
- ✅ `my-project/src/main.py` - All 6 breaking changes fixed
- ✅ `my-project/tests/test_main.py` - Tests still pass (no changes needed!)

### 2. Inspect the Code Changes

**`my-project/src/main.py`** - Look for these 6 fixes:

**Change #1 - Import path fixed (line 3):**
```python
# Before (v1.0):
from analytics import DataProcessor

# After (v2.0):
from analytics.core import Analyzer  ✅
```

**Change #2 & #3 - Class renamed + Constructor requires config (lines 16-17):**
```python
# Before (v1.0):
processor = DataProcessor()

# After (v2.0):
config = {'mode': 'standard'}  # v2.0 requires config ✅
processor = Analyzer(config)   # Class renamed ✅
```

**Change #4 - Method renamed (line 19):**
```python
# Before (v1.0):
result = processor.analyze(data)

# After (v2.0):
result = processor.process(data)  # analyze() → process() ✅
```

**Change #5 & #6 - Return type + Data access (lines 21-25):**
```python
# Before (v1.0):
return result  # Was a dict

# After (v2.0):
return {  # Convert AnalysisResult object to dict ✅
    'mean': result.statistics.mean,   # Object access ✅
    'count': result.statistics.count,
    'sum': result.statistics.total,   # 'sum' → 'total'
}
```

**`my-project/tests/test_main.py`** - No changes needed!

The tests didn't change because `calculate_metrics()` maintains the same dict interface for callers.

### 3. Run Tests Manually

```bash
cd my-project
source venv/bin/activate
pytest tests/ -v
```

**Expected output:**
```
============================= test session starts ==============================
test_main.py::test_calculate_metrics PASSED                        [ 50%]
test_main.py::test_main PASSED                                     [100%]

============================== 2 passed in 0.01s ===============================
```

### 4. Run the Program

```bash
cd my-project
source venv/bin/activate
python src/main.py
```

**Expected output:**
```
Data: [10, 20, 30, 40, 50]
Mean: 30.0
Count: 5
Sum: 150
```

### 5. Verify v2.0 is Installed

```bash
cd my-project
source venv/bin/activate
pip list | grep analytics
```

**Expected output:**
```
analytics    2.0.0    /path/to/examples/dependency-upgrade/analytics-v2
```

### Summary of All Changes

✅ **Import**: `analytics` → `analytics.core`
✅ **Class**: `DataProcessor` → `Analyzer`
✅ **Constructor**: Now requires `config` parameter
✅ **Method**: `analyze()` → `process()`
✅ **Return**: Dict → AnalysisResult object (handled internally)
✅ **Field**: `sum` → `total` (accessed via `.statistics.total`)

All 6 breaking changes successfully fixed by Claude! 🎉

## Example Output

### Before (v1.0 API)
```python
# src/main.py
from analytics import DataProcessor

def calculate_metrics(data):
    processor = DataProcessor()
    result = processor.analyze(data)
    return result

# Usage
result = calculate_metrics([10, 20, 30])
print(result['mean'])  # 20.0
```

### After (v2.0 API - fixed by AI)
```python
# src/main.py
from analytics.core import Analyzer

def calculate_metrics(data):
    analyzer = Analyzer(config={'mode': 'fast'})
    result = analyzer.process(data)
    return result

# Usage
result = calculate_metrics([10, 20, 30])
print(result.statistics.mean)  # 20.0
```

## Key Concepts Demonstrated

- **Pre-actions**: Run dependency upgrade before convergence loop
- **Multiple validators**: Import check + Syntax check + Tests
- **TestSuiteValidator**: Captures pytest output for AI analysis
- **Custom system prompts**: Define AI's role and task clearly
- **Iterative fixing**: AI makes changes, framework re-validates
- **Self-contained**: No external dependencies, fully reproducible

## Extending This Pattern

This example can be adapted for:

- **Different languages**: Go (go.mod), JavaScript (package.json), Ruby (Gemfile)
- **Different test frameworks**: unittest, jest, rspec
- **Multiple dependencies**: Upgrade several packages at once
- **More complex changes**: Database migrations, API version bumps
- **CI/CD integration**: Automate upgrades in your pipeline

## Troubleshooting

**Tests still fail after convergence**:
- Check `my-project/src/main.py` and `tests/test_main.py`
- Claude may need more context - increase `max_attempts` in config.yaml
- Add more detailed error messages to system prompt

**Import errors**:
- Ensure virtual environment is activated: `source my-project/venv/bin/activate`
- Check that analytics v2 is installed: `pip list | grep analytics`

**Setup fails**:
- Requires Python 3.11+ with venv module
- Check: `python3 --version`

