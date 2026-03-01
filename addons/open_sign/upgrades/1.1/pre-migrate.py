# Part of Odoo. See LICENSE file for full copyright and licensing details.


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", [table_name])
    return bool(cr.fetchone()[0])


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        [table_name, column_name],
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    del version

    if _table_exists(cr, 'open_sign_request'):
        if _column_exists(cr, 'open_sign_request', 'evidence_schema_version'):
            cr.execute(
                """
                UPDATE open_sign_request
                   SET evidence_schema_version = 'v1'
                 WHERE evidence_schema_version IS NULL
                    OR btrim(evidence_schema_version) = ''
                """
            )
            cr.execute(
                """
                UPDATE open_sign_request
                   SET evidence_schema_version = btrim(evidence_schema_version)
                 WHERE evidence_schema_version IS NOT NULL
                   AND evidence_schema_version <> btrim(evidence_schema_version)
                """
            )
        if _column_exists(cr, 'open_sign_request', 'lock_version'):
            cr.execute(
                """
                UPDATE open_sign_request
                   SET lock_version = 0
                 WHERE lock_version IS NULL
                    OR lock_version < 0
                """
            )

    if _table_exists(cr, 'open_sign_role'):
        if _column_exists(cr, 'open_sign_role', 'name'):
            cr.execute(
                """
                UPDATE open_sign_role
                   SET name = btrim(name)
                 WHERE name IS NOT NULL
                   AND name <> btrim(name)
                """
            )
            cr.execute(
                """
                UPDATE open_sign_role
                   SET name = CONCAT('Role ', id::text)
                 WHERE name IS NULL
                    OR btrim(name) = ''
                """
            )
            cr.execute(
                """
                WITH ranked AS (
                    SELECT id,
                           row_number() OVER (
                               PARTITION BY template_id, lower(name)
                               ORDER BY id
                           ) AS rank_order
                      FROM open_sign_role
                )
                UPDATE open_sign_role role
                   SET name = CONCAT(role.name, ' #', role.id::text)
                  FROM ranked
                 WHERE ranked.id = role.id
                   AND ranked.rank_order > 1
                """
            )
        if _column_exists(cr, 'open_sign_role', 'name_normalized'):
            cr.execute(
                """
                UPDATE open_sign_role
                   SET name_normalized = lower(name)
                 WHERE name IS NOT NULL
                """
            )
        if _column_exists(cr, 'open_sign_role', 'sequence'):
            cr.execute(
                """
                UPDATE open_sign_role
                   SET sequence = 0
                 WHERE sequence IS NULL
                    OR sequence < 0
                """
            )

    if _table_exists(cr, 'open_sign_template_field'):
        if _column_exists(cr, 'open_sign_template_field', 'label'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET label = btrim(label)
                 WHERE label IS NOT NULL
                   AND label <> btrim(label)
                """
            )
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET label = CONCAT('Field ', id::text)
                 WHERE label IS NULL
                    OR btrim(label) = ''
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'page'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET page = 1
                 WHERE page IS NULL
                    OR page < 1
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'x'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET x = LEAST(GREATEST(COALESCE(x, 0), 0), 1)
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'y'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET y = LEAST(GREATEST(COALESCE(y, 0), 0), 1)
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'width'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET width = CASE
                                   WHEN width IS NULL OR width <= 0 THEN 0.2
                                   WHEN width > 1 THEN 1
                                   ELSE width
                               END
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'height'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET height = CASE
                                    WHEN height IS NULL OR height <= 0 THEN 0.05
                                    WHEN height > 1 THEN 1
                                    ELSE height
                                END
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'sequence'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET sequence = 0
                 WHERE sequence IS NULL
                    OR sequence < 0
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'min_length'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET min_length = 0
                 WHERE min_length < 0
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'max_length'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET max_length = 0
                 WHERE max_length < 0
                """
            )
        if _column_exists(cr, 'open_sign_template_field', 'min_length') and _column_exists(cr, 'open_sign_template_field', 'max_length'):
            cr.execute(
                """
                UPDATE open_sign_template_field
                   SET max_length = min_length
                 WHERE min_length IS NOT NULL
                   AND max_length IS NOT NULL
                   AND max_length < min_length
                """
            )

    if _table_exists(cr, 'open_sign_template_field_option'):
        if _column_exists(cr, 'open_sign_template_field_option', 'value'):
            cr.execute(
                """
                UPDATE open_sign_template_field_option
                   SET value = btrim(value)
                 WHERE value IS NOT NULL
                   AND value <> btrim(value)
                """
            )
            cr.execute(
                """
                UPDATE open_sign_template_field_option
                   SET value = CONCAT('option_', id::text)
                 WHERE value IS NULL
                    OR btrim(value) = ''
                """
            )
            cr.execute(
                """
                WITH ranked AS (
                    SELECT id,
                           row_number() OVER (
                               PARTITION BY field_id, value
                               ORDER BY id
                           ) AS rank_order
                      FROM open_sign_template_field_option
                )
                UPDATE open_sign_template_field_option field_option
                   SET value = CONCAT(field_option.value, '_', field_option.id::text)
                  FROM ranked
                 WHERE ranked.id = field_option.id
                   AND ranked.rank_order > 1
                """
            )
        if _column_exists(cr, 'open_sign_template_field_option', 'label'):
            cr.execute(
                """
                UPDATE open_sign_template_field_option
                   SET label = btrim(label)
                 WHERE label IS NOT NULL
                   AND label <> btrim(label)
                """
            )
            cr.execute(
                """
                UPDATE open_sign_template_field_option
                   SET label = CONCAT('Option ', id::text)
                 WHERE label IS NULL
                    OR btrim(label) = ''
                """
            )
        if _column_exists(cr, 'open_sign_template_field_option', 'sequence'):
            cr.execute(
                """
                UPDATE open_sign_template_field_option
                   SET sequence = 0
                 WHERE sequence IS NULL
                    OR sequence < 0
                """
            )

    if _table_exists(cr, 'open_sign_request_signer'):
        if _column_exists(cr, 'open_sign_request_signer', 'sequence'):
            cr.execute(
                """
                UPDATE open_sign_request_signer
                   SET sequence = 0
                 WHERE sequence IS NULL
                    OR sequence < 0
                """
            )
        has_state = _column_exists(cr, 'open_sign_request_signer', 'state')
        has_signed_at = _column_exists(cr, 'open_sign_request_signer', 'signed_at')
        if has_state and has_signed_at:
            coalesce_parts = ['signed_at']
            if _column_exists(cr, 'open_sign_request_signer', 'last_opened_at'):
                coalesce_parts.append('last_opened_at')
            if _column_exists(cr, 'open_sign_request_signer', 'consent_accepted_at'):
                coalesce_parts.append('consent_accepted_at')
            coalesce_parts.extend(['write_date', 'create_date', 'NOW()'])
            signed_at_expr = f"COALESCE({', '.join(coalesce_parts)})"
            cr.execute(
                f"""
                UPDATE open_sign_request_signer
                   SET signed_at = {signed_at_expr}
                 WHERE state = 'signed'
                   AND signed_at IS NULL
                """
            )

    if _table_exists(cr, 'open_sign_audit_log') and _column_exists(cr, 'open_sign_audit_log', 'event_sequence'):
        cr.execute(
            """
            WITH problematic_requests AS (
                SELECT request_id
                  FROM open_sign_audit_log
                 GROUP BY request_id
                HAVING bool_or(event_sequence IS NULL OR event_sequence <= 0)
                    OR COUNT(*) <> COUNT(DISTINCT event_sequence)
            ),
            ordered AS (
                SELECT log.id,
                       row_number() OVER (
                           PARTITION BY log.request_id
                           ORDER BY COALESCE(log.event_at, log.create_date), log.id
                       ) AS normalized_sequence
                  FROM open_sign_audit_log log
                  JOIN problematic_requests problematic
                    ON problematic.request_id = log.request_id
            )
            UPDATE open_sign_audit_log log
               SET event_sequence = ordered.normalized_sequence
              FROM ordered
             WHERE ordered.id = log.id
            """
        )

    if _table_exists(cr, 'open_sign_template_version') and _column_exists(cr, 'open_sign_template_version', 'version_number'):
        cr.execute(
            """
            WITH problematic_templates AS (
                SELECT template_id
                  FROM open_sign_template_version
                 GROUP BY template_id
                HAVING bool_or(version_number IS NULL OR version_number <= 0)
                    OR COUNT(*) <> COUNT(DISTINCT version_number)
            ),
            ordered AS (
                SELECT template_version.id,
                       row_number() OVER (
                           PARTITION BY template_version.template_id
                           ORDER BY COALESCE(template_version.published_at, template_version.create_date), template_version.id
                       ) AS normalized_version
                  FROM open_sign_template_version template_version
                  JOIN problematic_templates problematic
                    ON problematic.template_id = template_version.template_id
            )
            UPDATE open_sign_template_version template_version
               SET version_number = ordered.normalized_version
              FROM ordered
             WHERE ordered.id = template_version.id
            """
        )
