# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
import re

from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


FIELD_TYPES_TEXTUAL = {'initials', 'name', 'email', 'phone', 'company', 'text', 'multiline', 'radio', 'selection'}
FIELD_TYPES_JSON_BOOL = {'checkbox'}
FIELD_TYPES_JSON_DICT = {'signature', 'stamp'}
FIELD_TYPES_DATE = {'date'}
FIELD_TYPES_STRIKETHROUGH = {'strikethrough'}
FIELD_TYPES_WITH_OPTIONS = {'radio', 'selection'}
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0B-\x1F\x7F]')
E164_PHONE_RE = re.compile(r'^\+?[0-9]{7,20}$')


def _is_present(value):
    if value in (False, None):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    return True


def _normalize_newlines(value):
    return (value or '').replace('\r\n', '\n').replace('\r', '\n')


def _assert_no_control_chars(value, error_message):
    if CONTROL_CHARS_RE.search(value or ''):
        raise ValidationError(error_message)


def _sanitize_date_string(iso_date):
    normalized_date = (iso_date or '').strip()
    try:
        date.fromisoformat(normalized_date)
    except ValueError as exc:
        raise ValidationError("Date values must use ISO-8601 format (YYYY-MM-DD).") from exc
    return normalized_date


def _normalize_option_value(template_field, option_value):
    normalized_input = (option_value or '').strip()
    if not normalized_input:
        return False
    option_by_key = {
        option.value.casefold(): option.value
        for option in template_field.option_ids
    }
    canonical_option = option_by_key.get(normalized_input.casefold())
    if not canonical_option:
        raise ValidationError("Value must match one of the configured options for this field.")
    return canonical_option


def _normalize_phone(value):
    normalized = re.sub(r'[\s().-]+', '', (value or '').strip())
    if normalized.startswith('00'):
        normalized = '+' + normalized[2:]
    if not E164_PHONE_RE.fullmatch(normalized):
        raise ValidationError("Phone values must be digits with an optional leading + and length between 7 and 20.")
    return normalized


def _apply_text_length_rules(template_field, normalized_text):
    if normalized_text in (False, None):
        return
    length = len(normalized_text)
    min_length = template_field.min_length or 0
    max_length = template_field.max_length or 0
    if min_length > 0 and length < min_length:
        raise ValidationError(f"Value length must be greater than or equal to {min_length}.")
    if max_length > 0 and length > max_length:
        raise ValidationError(f"Value length must be less than or equal to {max_length}.")


def _apply_regex_rule(template_field, normalized_text):
    if not template_field.validation_regex or normalized_text in (False, None):
        return
    if not re.fullmatch(template_field.validation_regex, normalized_text):
        raise ValidationError("Value does not match the field validation pattern.")


def _normalize_textual_value(template_field, value_text):
    field_type = template_field.type
    if value_text in (False, None):
        return False
    text_value = value_text if isinstance(value_text, str) else str(value_text)

    if field_type == 'multiline':
        normalized = _normalize_newlines(text_value).strip('\n')
        if not normalized.strip():
            return False
        _assert_no_control_chars(normalized, "Multiline values cannot contain control characters.")
        return normalized

    normalized = text_value.strip()
    if not normalized:
        return False

    if field_type == 'email':
        normalized_email = email_normalize(normalized)
        if not normalized_email:
            raise ValidationError("Value email must be a valid email address.")
        if len(normalized_email) > 254:
            raise ValidationError("Value email must be less than or equal to 254 characters.")
        return normalized_email

    if field_type == 'phone':
        return _normalize_phone(normalized)

    if field_type == 'initials':
        normalized = normalized.upper()
        if len(normalized) < 1 or len(normalized) > 8:
            raise ValidationError("Initials values must be between 1 and 8 characters.")
        return normalized

    if field_type in FIELD_TYPES_WITH_OPTIONS:
        return _normalize_option_value(template_field, normalized)

    if field_type == 'text' and '\n' in normalized:
        raise ValidationError("Single-line text values cannot contain newlines.")

    if field_type in {'name', 'company', 'text'}:
        _assert_no_control_chars(normalized, "Text values cannot contain control characters.")

    return normalized


def _normalize_json_value(template_field, value_json):
    field_type = template_field.type
    if value_json in (False, None):
        return False

    if field_type in FIELD_TYPES_JSON_BOOL:
        if isinstance(value_json, bool):
            return value_json
        raise ValidationError("Checkbox values must be booleans.")

    if field_type in FIELD_TYPES_DATE:
        if isinstance(value_json, str):
            return {'iso_date': _sanitize_date_string(value_json)}
        if isinstance(value_json, dict):
            iso_date = _sanitize_date_string(value_json.get('iso_date'))
            normalized_payload = {'iso_date': iso_date}
            timezone = (value_json.get('timezone') or '').strip()
            if timezone:
                normalized_payload['timezone'] = timezone
            return normalized_payload
        raise ValidationError("Date values must be an ISO string or a JSON object with iso_date.")

    if field_type in FIELD_TYPES_STRIKETHROUGH:
        if isinstance(value_json, bool):
            return {'applied': value_json}
        if isinstance(value_json, dict) and isinstance(value_json.get('applied'), bool):
            return {'applied': value_json['applied']}
        raise ValidationError("Strikethrough values must provide a boolean applied flag.")

    if field_type in FIELD_TYPES_JSON_DICT:
        if isinstance(value_json, dict):
            return value_json
        raise ValidationError("Signature and stamp values must be JSON objects.")

    return value_json


def normalize_and_validate_field_value(
    template_field,
    value_text,
    value_json,
    signed_payload_attachment,
    *,
    enforce_required=True,
):
    field_type = template_field.type
    normalized_text = value_text
    normalized_json = value_json

    if field_type in FIELD_TYPES_TEXTUAL:
        normalized_text = _normalize_textual_value(template_field, value_text)
        normalized_json = False
        _apply_text_length_rules(template_field, normalized_text)
        _apply_regex_rule(template_field, normalized_text)
    elif field_type in FIELD_TYPES_JSON_BOOL | FIELD_TYPES_JSON_DICT | FIELD_TYPES_DATE | FIELD_TYPES_STRIKETHROUGH:
        normalized_text = False
        normalized_json = _normalize_json_value(template_field, value_json)
    else:
        normalized_text = value_text
        normalized_json = value_json

    has_value = _is_present(normalized_text) or _is_present(normalized_json) or bool(signed_payload_attachment)
    if field_type in FIELD_TYPES_JSON_BOOL and isinstance(value_json, bool):
        has_value = True
    if enforce_required and template_field.required and not has_value:
        raise ValidationError(f"Required field {template_field.label} must have a value.")

    if field_type in FIELD_TYPES_JSON_DICT and has_value:
        if not _is_present(normalized_json):
            raise ValidationError("Signature and stamp values must be JSON objects.")
        if not signed_payload_attachment:
            raise ValidationError("Signature and stamp values require a signed payload attachment.")

    return normalized_text, normalized_json
