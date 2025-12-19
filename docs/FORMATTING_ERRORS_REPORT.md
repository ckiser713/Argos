# Formatting Errors Report

## Summary
Found **511 formatting errors** across the Python codebase, with **438 automatically fixable**.

## Error Breakdown

### Most Common Issues:
1. **W293** - Blank line contains whitespace: **337 occurrences** (fixable)
2. **I001** - Import block is un-sorted or un-formatted: **51 occurrences** (fixable)
3. **F401** - Unused imports: **41 occurrences** (fixable)
4. **W291** - Trailing whitespace: **36 occurrences** (fixable)
5. **E501** - Line too long (>120 chars): **20 occurrences** (not auto-fixable)
6. **E722** - Bare `except` clauses: **11 occurrences** (not auto-fixable)
7. **F841** - Unused variables: **6 occurrences** (not auto-fixable)
8. **E402** - Module import not at top of file: **2 occurrences** (not auto-fixable)
9. **F821** - Undefined name: **2 occurrences** (not auto-fixable)
10. **Other issues**: 5 occurrences (various)

## Configuration Issue

⚠️ **Warning**: The `ruff.toml` file uses deprecated top-level linter settings. The `select` option should be moved to `[lint]` section.

Current (deprecated):
```toml
select = ["E", "F", "W", "I", "N"]
```

Should be:
```toml
[lint]
select = ["E", "F", "W", "I", "N"]
```

## Files Needing Formatting

**45 Python files** need reformatting according to Ruff's formatter:
- All files in `backend/app/api/routes/` (14 files)
- All files in `backend/app/domain/` (5 files)
- All files in `backend/app/services/` (17 files)
- All files in `backend/app/repos/` (5 files)
- Other backend files (4 files)

## TypeScript/Frontend

- TypeScript compiler not available (needs `npm install` in frontend directory)
- One linter error found: Missing `@types/node` type definition file

## Recommendations

### Quick Fixes (Automatically Fixable):
```bash
cd /home/nexus/Argos_Chatgpt
source backend/.venv/bin/activate
ruff check --fix backend/
ruff format backend/
```

This will fix:
- 337 blank lines with whitespace
- 51 unsorted imports
- 41 unused imports
- 36 trailing whitespace issues
- 1 f-string without placeholders
- 1 redefined variable
- 1 missing newline at end of file

### Manual Fixes Required:
1. **20 lines too long** - Need to break into multiple lines
2. **11 bare except clauses** - Should specify exception types
3. **6 unused variables** - Remove or use them
4. **2 undefined names** - Fix missing imports (e.g., `Dict` in some files)
5. **2 module imports not at top** - Move imports to top of file
6. **1 undefined local variable** - Fix variable scope issue in `streaming.py`
7. **1 mixed-case variable** - Fix naming convention in `models.py`

## Critical Issues to Address

1. **`backend/app/api/routes/streaming.py`**:
   - Line 99: Local variable `job` referenced before assignment (F823)
   - Line 118: Local variable `job` assigned but never used (F841)

2. **`backend/app/api/routes/project_intel.py`**:
   - Line 31: Undefined name `Dict` (F821) - needs `from typing import Dict`

3. **`backend/tests/test_mode_integration.py`**:
   - Line 14: Undefined name `Dict` (F821) - needs import

4. **`backend/app/repos/project_intel_repo.py`**:
   - Line 240: Redefinition of unused `timezone` (F811)

5. **`backend/app/domain/models.py`**:
   - Line 416: Variable `useVectorSearch` should use snake_case (N815)

## Next Steps

1. Fix the `ruff.toml` configuration deprecation warning
2. Run automatic fixes: `ruff check --fix backend/ && ruff format backend/`
3. Manually fix the 73 non-auto-fixable errors
4. Install TypeScript dependencies in frontend and check for formatting issues
5. Consider adding pre-commit hooks to prevent future formatting issues

