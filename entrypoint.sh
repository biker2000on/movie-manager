#!/bin/bash
set -e

# Determine keep list path (exported for Python subprocess)
export KEEP_LIST_PATH="${KEEP_LIST_PATH:-/data/.keep-list.json}"

# Ensure data directory exists and is writable
if [[ ! -d "$(dirname "$KEEP_LIST_PATH")" ]]; then
    echo "Warning: Data directory does not exist: $(dirname "$KEEP_LIST_PATH")"
fi

# If first argument is a recognized command, run the filter
case "$1" in
    scan|delete|keep|--help|-h)
        exec python radarr_horror_filter.py "$@"
        ;;
    bash|sh)
        # Allow shell access for debugging
        exec "$@"
        ;;
    python)
        # Allow direct Python access
        shift
        exec python "$@"
        ;;
    "")
        # No arguments - show help
        exec python radarr_horror_filter.py --help
        ;;
    *)
        # Unknown command - pass through to Python
        exec python radarr_horror_filter.py "$@"
        ;;
esac
