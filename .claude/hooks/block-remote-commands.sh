#!/bin/bash
# Hook script to enforce local development safeguards
# Blocks commands that interact with remote/production Supabase
#
# BLOCKED:
#   - supabase link        → Connects to remote project
#   - supabase db push     → Modifies remote database
#   - supabase db pull     → Downloads from remote (can overwrite local)
#   - npm run build        → May connect to remote during build
#
# ALLOWED:
#   - supabase start/stop/status
#   - supabase db reset
#   - supabase migration new
#   - npx tsc

TOOL_INPUT="$1"

# Block 'supabase link' - connects to remote project
if echo "$TOOL_INPUT" | grep -qE 'supabase\s+link'; then
  cat << 'EOF'
{
  "decision": "block",
  "reason": "BLOCKED: 'supabase link' connects to remote/production Supabase.\n\nThis project uses LOCAL Supabase only (Docker).\nNO remote connection is needed for development.\n\nUse local commands:\n  - npx supabase start    (start local containers)\n  - npx supabase db reset (apply migrations locally)"
}
EOF
  exit 0
fi

# Block 'supabase push' or 'supabase db push' - modifies remote DB
if echo "$TOOL_INPUT" | grep -qE 'supabase\s+(db\s+)?push'; then
  cat << 'EOF'
{
  "decision": "block",
  "reason": "BLOCKED: 'supabase push' modifies the REMOTE/PRODUCTION database.\n\nUse local commands instead:\n  - npx supabase db reset    (reset local DB with migrations)\n  - npx supabase migration new (create new migration)\n\nTo push to production, do it manually outside Claude Code."
}
EOF
  exit 0
fi

# Block 'supabase db pull' - downloads from remote (can overwrite local migrations)
if echo "$TOOL_INPUT" | grep -qE 'supabase\s+db\s+pull'; then
  cat << 'EOF'
{
  "decision": "block",
  "reason": "BLOCKED: 'supabase db pull' downloads schema from REMOTE/PRODUCTION.\n\nThis can overwrite your local migrations.\nThe migration files in supabase/migrations/ are the source of truth.\n\nUse local commands:\n  - npx supabase db reset (apply existing migrations)"
}
EOF
  exit 0
fi

# Block 'npm run build' / 'pnpm build' / 'yarn build' - may connect to remote
if echo "$TOOL_INPUT" | grep -qE '(npm|pnpm|yarn)\s+(run\s+)?build'; then
  cat << 'EOF'
{
  "decision": "block",
  "reason": "BLOCKED: 'npm run build' may connect to remote Supabase during build.\n\nUse TypeScript type checking instead:\n  - npx tsc --noEmit    (check types without building)\n  - npx tsc             (compile TypeScript)\n\nTo run a full build, do it manually outside Claude Code."
}
EOF
  exit 0
fi

# Allow all other commands
exit 0
