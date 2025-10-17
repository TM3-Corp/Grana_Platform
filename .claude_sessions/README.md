# 🤖 Claude Code Session Work Directory

**⚠️ CRITICAL: Files in this directory are NEVER committed to git**

## Purpose

This directory contains temporary work from Claude Code sessions that should never reach production:
- Debugging scripts and exploration code
- Temporary test files (not proper unit tests)
- Session documentation and work-in-progress notes
- API testing and verification scripts
- Data exploration and analysis

## Directory Structure

```
.claude_sessions/
├── current/          # Active session work
├── archive/          # Completed session artifacts (for reference)
├── tests/            # Temporary test scripts (NOT unit tests)
├── debugging/        # Debug scripts and temporary fixes
└── exploration/      # Code exploration and research
```

## Rules

### ✅ DO put here:
- Temporary debugging scripts (e.g., `debug_api_response.py`)
- Exploration code to understand the codebase
- Session notes and work documentation
- Quick tests to verify something works
- Data analysis scripts used during development
- API endpoint testing scripts

### ❌ DO NOT put here:
- Production code (goes in `backend/`, `frontend/`, etc.)
- Proper unit tests (goes in `backend/tests/`, `frontend/__tests__/`)
- Configuration files needed in production
- Migration scripts that should be versioned
- Any code that needs to run in production

## When to Use Production Paths

**Production code should be committed:**
- Backend APIs, services, repositories (`backend/app/`)
- Frontend components, pages, utilities (`frontend/`)
- Proper unit tests with pytest/jest (`backend/tests/`, `frontend/__tests__/`)
- Migration scripts (`backend/alembic/versions/` or `backend/scripts/migrations/`)
- Configuration files (`.env.example`, `config.py`)

## Example Session Workflow

```bash
# ❌ WRONG: Writing session work to production path
$ echo "print('Testing API')" > backend/test_api.py
$ git add backend/test_api.py  # This pollutes production!

# ✅ CORRECT: Writing session work to .claude_sessions
$ echo "print('Testing API')" > .claude_sessions/current/test_api.py
# This file is .gitignored and never committed
```

## Cleanup

Session work files can be deleted or archived when no longer needed:
```bash
# Archive completed session work
mv .claude_sessions/current/* .claude_sessions/archive/$(date +%Y-%m-%d)/

# Or simply delete
rm -rf .claude_sessions/current/*
```

---

**Remember**: If you're unsure whether something is session work or production code, ask:
- "Will this code run in production?" → Production path
- "Is this just for our current debugging session?" → `.claude_sessions/`
