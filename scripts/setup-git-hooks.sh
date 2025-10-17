#!/bin/bash
# Setup Git Hooks for Session Work Protection
#
# This script installs a pre-commit hook that prevents session artifacts
# from being committed to the repository.
#
# Usage:
#   ./scripts/setup-git-hooks.sh
#
# The hook will automatically block commits containing:
#   - Files in .claude_sessions/
#   - Files matching session_*.py, session_*.ts patterns
#   - Files matching debug_temp_*, exploration_* patterns

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_PATH="$REPO_ROOT/.git/hooks/pre-commit"

echo "🔧 Setting up Git hooks for session work protection..."
echo ""

# Check if we're in a git repository
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ ERROR: Not in a git repository"
    echo "   Current directory: $REPO_ROOT"
    exit 1
fi

# Create the pre-commit hook
cat > "$HOOK_PATH" << 'EOF'
#!/bin/bash
# Pre-commit hook to prevent session artifacts from being committed
# This runs BEFORE every git commit

echo "🔍 Checking for session artifacts..."

# Check if any .claude_sessions files are staged
if git diff --cached --name-only | grep -q "^\.claude_sessions/"; then
    echo "❌ ERROR: Attempting to commit files from .claude_sessions/"
    echo ""
    echo "Files blocked:"
    git diff --cached --name-only | grep "^\.claude_sessions/"
    echo ""
    echo "💡 TIP: Session work should stay in .claude_sessions/ and never be committed."
    echo "    If this is production code, move it to the proper directory first."
    echo ""
    exit 1
fi

# Check for common session artifact patterns
BLOCKED_PATTERNS=(
    "session_.*\\.py$"
    "session_.*\\.ts$"
    "session_.*\\.md$"
    "debug_temp_"
    "exploration_.*\\.py$"
    "_session_work/"
    "_claude_work/"
)

for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if git diff --cached --name-only | grep -qE "$pattern"; then
        echo "❌ ERROR: Attempting to commit session artifact matching pattern: $pattern"
        echo ""
        echo "Files blocked:"
        git diff --cached --name-only | grep -E "$pattern"
        echo ""
        echo "💡 TIP: This looks like session work. Move it to .claude_sessions/ first."
        echo ""
        exit 1
    fi
done

# Check for files in backend/scripts/debug/ (these should be temporary)
if git diff --cached --name-only | grep -q "^backend/scripts/debug/.*\\.py$"; then
    echo "⚠️  WARNING: Committing files in backend/scripts/debug/"
    echo ""
    echo "Files:"
    git diff --cached --name-only | grep "^backend/scripts/debug/"
    echo ""
    echo "❓ Are these temporary debug scripts or permanent utilities?"
    echo "   - Temporary → Move to .claude_sessions/debugging/"
    echo "   - Permanent → Keep in backend/scripts/debug/ (but document why)"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ No session artifacts detected. Commit allowed."
exit 0
EOF

# Make the hook executable
chmod +x "$HOOK_PATH"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "📋 The hook will now automatically prevent:"
echo "   • Files in .claude_sessions/ from being committed"
echo "   • Files matching session_*.py, session_*.ts patterns"
echo "   • Files matching debug_temp_*, exploration_* patterns"
echo ""
echo "🧪 Test the hook with:"
echo "   echo '# test' > .claude_sessions/current/test.py"
echo "   git add -f .claude_sessions/current/test.py"
echo "   git commit -m 'test'  # Should be blocked"
echo ""
echo "🚀 The hook is active for this repository!"
