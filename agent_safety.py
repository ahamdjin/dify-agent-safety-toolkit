"""Bounded, deterministic helpers for preparing agent inputs.

Not DLP, anonymization, compliance certification, or a secret scanner.
Raw content never appears in exception messages from this module.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict
from typing import Any

from gpt_tools.pii_redactor import redact_text
from gpt_tools.tool_output_compactor import CompactionStats, compact

MAX_INPUT_CHARS = 120_000
MAX_OUTPUT_CHARS = 150_000
MAX_JSON_NESTING = 32
MASK = "[REDACTED]"

SENSITIVE_KEYS = frozenset({
    "authorization", "proxy_authorization", "password", "passwd", "secret",
    "api_key", "apikey", "x_api_key", "client_secret", "private_key",
    "access_token", "refresh_token", "id_token", "auth_token", "cookie",
    "set_cookie", "session_id", "session_token", "jwt", "credentials",
})


def _check_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if len(value) > MAX_INPUT_CHARS:
        raise ValueError(f"{field} is too large (maximum {MAX_INPUT_CHARS} characters)")
    return value


def _limit(value: Any, default: int, minimum: int, maximum: int, name: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise ValueError(f"{name} must be an integer")
    result = int(value)
    if not minimum <= result <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return result


def _sensitive_key(value: str) -> bool:
    # Supports common JSON conventions: accessToken, access_token, access-token.
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return (
        normalized in SENSITIVE_KEYS
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
        or normalized.endswith("_api_key")
    )


def redact_sensitive_text(text: str) -> dict[str, Any]:
    source = _check_text(text, "text")
    result = redact_text(source)
    if len(result.text) > MAX_OUTPUT_CHARS:
        raise ValueError("Sanitized result exceeds output size limit")
    return {
        "text": result.text,
        "changed": result.text != source,
        "redaction_counts": result.counts,
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contains duplicate field names")
        result[key] = value
    return result


def _reject_non_json_constant(value: str) -> None:
    raise ValueError("JSON contains a non-standard numeric constant")


def _prepare_values(value: Any, totals: Counter[str], *, depth: int = 0) -> Any:
    if depth > MAX_JSON_NESTING:
        raise ValueError("JSON is nested too deeply")
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            if _sensitive_key(key):
                cleaned[key] = MASK
                totals["FIELDS"] += 1
            else:
                cleaned[key] = _prepare_values(child, totals, depth=depth + 1)
        return cleaned
    if isinstance(value, list):
        return [_prepare_values(child, totals, depth=depth + 1) for child in value]
    if isinstance(value, str):
        result = redact_text(value)
        totals.update(result.counts)
        return result.text
    return value


def prepare_agent_json(
    json_text: str,
    max_string: int = 1000,
    max_items: int = 25,
    max_depth: int = 8,
) -> dict[str, Any]:
    source = _check_text(json_text, "json_text")
    string_limit = _limit(max_string, 1000, 100, 4000, "max_string")
    items_limit = _limit(max_items, 25, 1, 100, "max_items")
    depth_limit = _limit(max_depth, 8, 1, 16, "max_depth")
    try:
        parsed = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_json_constant,
        )
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise ValueError("json_text must contain valid JSON within nesting limits") from None
    redactions: Counter[str] = Counter()
    prepared = _prepare_values(parsed, redactions)
    stats = CompactionStats()
    result = compact(
        prepared,
        max_string=string_limit,
        max_items=items_limit,
        max_depth=depth_limit,
        stats=stats,
    )
    serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(serialized) > MAX_OUTPUT_CHARS:
        raise ValueError("Prepared JSON exceeds output size limit")
    return {
        "json_text": serialized,
        "changed": serialized != source,
        "input_characters": len(source),
        "output_characters": len(serialized),
        "redaction_counts": dict(redactions),
        "compaction": asdict(stats),
    }
