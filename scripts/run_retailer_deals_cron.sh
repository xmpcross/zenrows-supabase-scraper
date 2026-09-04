#!/usr/bin/env bash
set -uo pipefail

readonly PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly RETAILER="${1:-}"

case "$RETAILER" in
  amazon_us|amazon_au|amazon_uk|bestbuy|ebay_us|ebay_au|walmart|iherb|sephora|target|newegg) ;;
  *)
    echo "Usage: $0 {amazon_us|amazon_au|amazon_uk|bestbuy|ebay_us|ebay_au|walmart|iherb|sephora|target|newegg}" >&2
    exit 2
    ;;
esac

cd "$PROJECT_DIR"
install -d -o root -g root -m 755 "$PROJECT_DIR/logs"
readonly LOG_FILE="$PROJECT_DIR/logs/${RETAILER}.log"

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  readonly PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  readonly PYTHON_EXEC="$(command -v python3)"
else
  echo "[$(date -Is)] Python is unavailable" >> "$LOG_FILE"
  exit 127
fi

echo "[$(date -Is)] Starting retailer deals ingestion: $RETAILER" >> "$LOG_FILE"
"$PYTHON_EXEC" run_nxt_bargains_pipeline.py \
  --provider zenrows \
  --deal-target "$RETAILER" >> "$LOG_FILE" 2>&1
exit_code=$?
echo "[$(date -Is)] Retailer ingestion finished: $RETAILER (exit $exit_code)" >> "$LOG_FILE"
echo >> "$LOG_FILE"
exit "$exit_code"
