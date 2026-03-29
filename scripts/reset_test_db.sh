#!/usr/bin/env bash
set -euo pipefail

DB_NAME=""
CONF_FILE=".devcontainer/odoo.conf"
DB_HOST=""
DB_PORT=""
DB_USER=""
DB_PASSWORD=""
MAINTENANCE_DB="postgres"

usage() {
    cat <<'EOF'
Usage: scripts/reset_test_db.sh [options]

Options:
      --db <name>            Database name to drop/recreate (required)
  -c, --config <path>        Odoo config file path (default: .devcontainer/odoo.conf)
      --db-host <host>       PostgreSQL host override
      --db-port <port>       PostgreSQL port override
      --db-user <user>       PostgreSQL user override
      --db-password <pass>   PostgreSQL password override
      --postgres-db <name>   Maintenance database to connect to (default: postgres)
  -h, --help                 Show this help message
EOF
}

read_config_option() {
    local file="$1"
    local key="$2"
    awk -F= -v wanted_key="$key" '
        /^\[options\][[:space:]]*$/ { in_options = 1; next }
        /^\[/ { in_options = 0 }
        in_options {
            key = $1
            sub(/^[[:space:]]+/, "", key)
            sub(/[[:space:]]+$/, "", key)
            if (key == wanted_key) {
                value = substr($0, index($0, "=") + 1)
                sub(/^[[:space:]]+/, "", value)
                sub(/[[:space:]]+$/, "", value)
                print value
                exit
            }
        }
    ' "$file"
}

resolve_option() {
    local current_value="$1"
    local config_key="$2"
    local default_value="${3-}"
    local resolved_value="$current_value"

    if [[ -z "$resolved_value" && -f "$CONF_FILE" ]]; then
        resolved_value="$(read_config_option "$CONF_FILE" "$config_key")"
    fi
    if [[ -z "$resolved_value" ]]; then
        resolved_value="$default_value"
    fi
    printf '%s' "$resolved_value"
}

quote_sql_identifier() {
    local identifier="$1"
    identifier="${identifier//\"/\"\"}"
    printf '"%s"' "$identifier"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db)
            DB_NAME="$2"
            shift 2
            ;;
        -c|--config)
            CONF_FILE="$2"
            shift 2
            ;;
        --db-host)
            DB_HOST="$2"
            shift 2
            ;;
        --db-port)
            DB_PORT="$2"
            shift 2
            ;;
        --db-user)
            DB_USER="$2"
            shift 2
            ;;
        --db-password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        --postgres-db)
            MAINTENANCE_DB="$2"
            shift 2
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

if [[ -z "$DB_NAME" ]]; then
    echo "Database name is required (--db)."
    usage
    exit 2
fi

if [[ ! -f "$CONF_FILE" ]]; then
    echo "Config file not found: $CONF_FILE"
    exit 2
fi

DB_HOST="$(resolve_option "$DB_HOST" db_host "")"
DB_PORT="$(resolve_option "$DB_PORT" db_port "5432")"
DB_USER="$(resolve_option "$DB_USER" db_user "")"
DB_PASSWORD="$(resolve_option "$DB_PASSWORD" db_password "")"

if [[ "$DB_NAME" == "$MAINTENANCE_DB" ]]; then
    echo "Refusing to reset maintenance database: $DB_NAME"
    exit 2
fi

DROP_SQL="DROP DATABASE IF EXISTS $(quote_sql_identifier "$DB_NAME") WITH (FORCE);"
CREATE_SQL="CREATE DATABASE $(quote_sql_identifier "$DB_NAME")"
if [[ -n "$DB_USER" ]]; then
    CREATE_SQL+=" OWNER $(quote_sql_identifier "$DB_USER")"
fi
CREATE_SQL+=";"

PSQL_ARGS=(-v ON_ERROR_STOP=1)
if [[ -n "$DB_HOST" ]]; then
    PSQL_ARGS+=(-h "$DB_HOST")
fi
if [[ -n "$DB_PORT" ]]; then
    PSQL_ARGS+=(-p "$DB_PORT")
fi
if [[ -n "$DB_USER" ]]; then
    PSQL_ARGS+=(-U "$DB_USER")
fi
PSQL_ARGS+=(-d "$MAINTENANCE_DB")

echo "Resetting database $DB_NAME via ${DB_HOST:-local socket}:${DB_PORT:-default}"
if [[ -n "$DB_PASSWORD" ]]; then
    PGPASSWORD="$DB_PASSWORD" psql "${PSQL_ARGS[@]}" -c "$DROP_SQL"
    PGPASSWORD="$DB_PASSWORD" psql "${PSQL_ARGS[@]}" -c "$CREATE_SQL"
else
    psql "${PSQL_ARGS[@]}" -c "$DROP_SQL"
    psql "${PSQL_ARGS[@]}" -c "$CREATE_SQL"
fi
