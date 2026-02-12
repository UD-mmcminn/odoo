#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${ODOO_RC:-/etc/odoo/odoo.conf}"
DATA_DIR="${ODOO_DATA_DIR:-/var/lib/odoo}"

mkdir -p "$(dirname "$CONFIG_FILE")" "$DATA_DIR"

if [[ ! -f "$CONFIG_FILE" || "${ODOO_FORCE_CONFIG:-0}" == "1" ]]; then
    {
        echo "[options]"
        echo "addons_path = ${ODOO_ADDONS_PATH:-/opt/odoo/odoo/addons,/opt/odoo/addons}"
        echo "data_dir = ${DATA_DIR}"
        echo "admin_passwd = ${ODOO_ADMIN_PASSWORD:-admin}"
        echo "db_host = ${ODOO_DB_HOST:-postgres}"
        echo "db_port = ${ODOO_DB_PORT:-5432}"
        echo "db_user = ${ODOO_DB_USER:-odoo}"
        echo "db_password = ${ODOO_DB_PASSWORD:-odoo}"
        echo "db_name = ${ODOO_DB_NAME:-False}"
        echo "http_port = ${ODOO_HTTP_PORT:-8069}"
        echo "longpolling_port = ${ODOO_LONGPOLLING_PORT:-8072}"

        if [[ -n "${ODOO_DB_FILTER:-}" ]]; then
            echo "dbfilter = ${ODOO_DB_FILTER}"
        fi
        if [[ -n "${ODOO_PROXY_MODE:-}" ]]; then
            echo "proxy_mode = ${ODOO_PROXY_MODE}"
        fi
        if [[ -n "${ODOO_WORKERS:-}" ]]; then
            echo "workers = ${ODOO_WORKERS}"
        fi
        if [[ -n "${ODOO_MAX_CRON_THREADS:-}" ]]; then
            echo "max_cron_threads = ${ODOO_MAX_CRON_THREADS}"
        fi
        if [[ -n "${ODOO_LIST_DB:-}" ]]; then
            echo "list_db = ${ODOO_LIST_DB}"
        fi
        if [[ -n "${ODOO_LOG_LEVEL:-}" ]]; then
            echo "log_level = ${ODOO_LOG_LEVEL}"
        fi
        if [[ -n "${ODOO_LOG_HANDLER:-}" ]]; then
            echo "log_handler = ${ODOO_LOG_HANDLER}"
        fi
        if [[ -n "${ODOO_LOGFILE:-}" ]]; then
            echo "logfile = ${ODOO_LOGFILE}"
        fi
        if [[ -n "${ODOO_LIMIT_TIME_CPU:-}" ]]; then
            echo "limit_time_cpu = ${ODOO_LIMIT_TIME_CPU}"
        fi
        if [[ -n "${ODOO_LIMIT_TIME_REAL:-}" ]]; then
            echo "limit_time_real = ${ODOO_LIMIT_TIME_REAL}"
        fi
        if [[ -n "${ODOO_LIMIT_MEMORY_HARD:-}" ]]; then
            echo "limit_memory_hard = ${ODOO_LIMIT_MEMORY_HARD}"
        fi
        if [[ -n "${ODOO_LIMIT_MEMORY_SOFT:-}" ]]; then
            echo "limit_memory_soft = ${ODOO_LIMIT_MEMORY_SOFT}"
        fi
    } > "$CONFIG_FILE"
fi

exec /opt/odoo/odoo-bin -c "$CONFIG_FILE" "$@"
