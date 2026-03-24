#!/usr/bin/env bash
set -euo pipefail

DB_NAME="test_open_sign"
CONF_FILE=".devcontainer/odoo.conf"
SKIP_WEB=0
SKIP_PORTAL=0
HTTP_PORT_BASE=8070

usage() {
    cat <<'EOF'
Usage: scripts/review_gate_open_sign.sh [options]

Options:
  -d, --db <name>         Database name (default: test_open_sign)
  -c, --config <path>     Odoo config file path (default: .devcontainer/odoo.conf)
      --http-port-base <n>
                          Base HTTP port for sequential Odoo runs (default: 8070)
      --skip-web          Skip /open_sign_web test run
      --skip-portal       Skip /open_sign_portal test run
  -h, --help              Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--db)
            DB_NAME="$2"
            shift 2
            ;;
        -c|--config)
            CONF_FILE="$2"
            shift 2
            ;;
        --http-port-base)
            HTTP_PORT_BASE="$2"
            shift 2
            ;;
        --skip-web)
            SKIP_WEB=1
            shift
            ;;
        --skip-portal)
            SKIP_PORTAL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 2
            ;;
    esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "$CONF_FILE" ]]; then
    echo "Config file not found: $CONF_FILE"
    exit 2
fi

echo "[1/6] Upgrade open_sign modules..."
./odoo-bin -c "$CONF_FILE" -d "$DB_NAME" --http-port="$HTTP_PORT_BASE" -u open_sign,open_sign_web,open_sign_portal --stop-after-init

echo "[2/6] Run backend test scope (/open_sign)..."
./odoo-bin -c "$CONF_FILE" -d "$DB_NAME" --http-port="$((HTTP_PORT_BASE + 1))" --test-enable --test-tags /open_sign --stop-after-init

if [[ "$SKIP_WEB" -eq 0 ]]; then
    echo "[3/6] Run frontend test scope (/open_sign_web)..."
    ./odoo-bin -c "$CONF_FILE" -d "$DB_NAME" --http-port="$((HTTP_PORT_BASE + 2))" --test-enable --test-tags /open_sign_web --stop-after-init
else
    echo "[3/6] Skipping frontend test scope (--skip-web)."
fi

if [[ "$SKIP_PORTAL" -eq 0 ]]; then
    echo "[4/6] Run portal test scope (/open_sign_portal)..."
    ./odoo-bin -c "$CONF_FILE" -d "$DB_NAME" --http-port="$((HTTP_PORT_BASE + 3))" --test-enable --test-tags /open_sign_portal --stop-after-init
else
    echo "[4/6] Skipping portal test scope (--skip-portal)."
fi

echo "[5/6] Scan for deprecated access-check APIs..."
found_deprecated=0

if rg -n "check_access_rights\\(" addons/open_sign addons/open_sign_web addons/open_sign_portal; then
    echo "Deprecated API usage found: check_access_rights("
    found_deprecated=1
fi

if rg -n "check_field_access_rights\\(" addons/open_sign addons/open_sign_web addons/open_sign_portal; then
    echo "Deprecated API usage found: check_field_access_rights("
    found_deprecated=1
fi

if [[ "$found_deprecated" -ne 0 ]]; then
    echo "Review gate failed due to deprecated API usage."
    exit 1
fi

echo "[6/6] Manual closeout reminder..."
echo "Run REVIEW_CHECKLIST.md before closing the task."
echo "Review gate passed."
