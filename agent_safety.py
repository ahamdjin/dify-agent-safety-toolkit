"""Deterministic, bounded preparation of Dify agent inputs.

Best-effort masking and a workflow policy signal, NOT DLP or safe-content proof.
Errors must never include the user's actual text, JSON values, or mask literals.
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
MAX_PATHS = 32
MAX_CUSTOM_KEYS = 32
MAX_CUSTOM_LITERALS = 20
MASK = "[REDACTED]"
MISSING = object()

SENSITIVE_KEYS = frozenset({
    "authorization", "proxy_authorization", "password", "passwd", "secret",
    "api_key", "apikey", "x_api_key", "client_secret", "private_key",
    "access_token", "refresh_token", "id_token", "auth_token", "cookie",
    "set_cookie", "session_id", "session_token", "jwt", "credentials",
})
PATH_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}(?:\[\])?$")
FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")


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


def _bool(value: Any, default: bool, field: str) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be true or false")
    return value


def _normalized_name(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")


def _sensitive_key(value: str, extra: frozenset[str]) -> bool:
    normalized = _normalized_name(value)
    return (
        normalized in SENSITIVE_KEYS
        or normalized in extra
        or normalized.endswith(("_token", "_secret", "_password", "_api_key"))
    )


def _mask_literals(value: str, literals: tuple[str, ...], counts: Counter[str]) -> str:
    for literal in literals:
        if literal in value:
            hits = value.count(literal)
            value = value.replace(literal, "[CUSTOM_MASK]")
            counts["CUSTOM"] += hits
    return value


def _read_literals(raw: str | None) -> tuple[str, ...]:
    if raw is None or raw == "":
        return ()
    if not isinstance(raw, str) or len(raw) > 4096:
        raise ValueError("mask_literals must be a short newline-separated string")
    items = tuple(dict.fromkeys(line.strip() for line in raw.splitlines() if line.strip()))
    if len(items) > MAX_CUSTOM_LITERALS or any(not 4 <= len(item) <= 128 for item in items):
        raise ValueError("mask_literals must have at most 20 unique entries of 4-128 characters")
    return items


def _read_key_names(raw: str | None) -> frozenset[str]:
    if raw is None or raw == "":
        return frozenset()
    if not isinstance(raw, str) or len(raw) > 4096:
        raise ValueError("additional_secret_keys must be a short comma/newline-separated string")
    lines = [line.strip() for line in re.split(r"[,\n]", raw) if line.strip()]
    if len(lines) > MAX_CUSTOM_KEYS or any(not FIELD_NAME.fullmatch(item) for item in lines):
        raise ValueError("additional_secret_keys must contain at most 32 simple field names")
    return frozenset(_normalized_name(item) for item in lines)


def _parse_paths(raw: str | None, field: str) -> tuple[tuple[str, ...], ...]:
    if raw is None or raw == "":
        return ()
    if not isinstance(raw, str) or len(raw) > 4096:
        raise ValueError(f"{field} must be a short comma/newline-separated string")
    lines = [line.strip() for line in re.split(r"[,\n]", raw) if line.strip()]
    if len(lines) > MAX_PATHS:
        raise ValueError(f"{field} must contain no more than {MAX_PATHS} paths")
    output: list[tuple[str, ...]] = []
    for line in lines:
        parts = tuple(line.split("."))
        if len(parts) > 12 or any(not PATH_PART.fullmatch(part) for part in parts):
            raise ValueError(f"{field} contains an invalid field path")
        if parts not in output:
            output.append(parts)
    return tuple(output)


def _path_covered(required: tuple[str, ...], allowed: tuple[tuple[str, ...], ...]) -> bool:
    # Selecting a parent subtree covers requirements for that subtree.
    return any(required[:len(path)] == path for path in allowed)


def _selection_tree(paths: tuple[tuple[str, ...], ...]) -> dict:
    tree: dict = {}
    for path in paths:
        node = tree
        for part in path:
            if node.get("__all__"):
                break
            node = node.setdefault(part, {})
        else:
            node.clear()
            node["__all__"] = True
    return tree


def _project(value: Any, tree: dict) -> Any:
    if tree.get("__all__"):
        return value
    if not isinstance(value, dict):
        return MISSING
    projected: dict[str, Any] = {}
    for spec, sub_tree in tree.items():
        if spec == "__all__":
            continue
        many = spec.endswith("[]")
        key = spec[:-2] if many else spec
        if key not in value:
            continue
        child = value[key]
        if many:
            if not isinstance(child, list):
                continue
            picked = [_project(item, sub_tree) for item in child]
            projected[key] = [item for item in picked if item is not MISSING]
        else:
            selected = _project(child, sub_tree)
            if selected is not MISSING:
                projected[key] = selected
    return projected


def _has_real_selection(value: Any) -> bool:
    """Do not treat empty wrapper objects like {"lead": {}} as useful context."""
    if isinstance(value, dict):
        return any(_has_real_selection(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_real_selection(child) for child in value)
    return value is not None and value != ""


def _truncation_marker(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.search(r"…\[truncated \d+ chars\]$", value))


def _count_fields(value: Any) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_count_fields(child) for child in value.values())
    if isinstance(value, list):
        return sum(_count_fields(child) for child in value)
    return 0


def _has_required(value: Any, path: tuple[str, ...]) -> bool:
    if not path:
        if value is None or value in ("", MASK, "[MAX_DEPTH_REACHED]") or _truncation_marker(value):
            return False
        if isinstance(value, (list, dict)) and not value:
            return False
        return True
    part = path[0]
    many = part.endswith("[]")
    key = part[:-2] if many else part
    if not isinstance(value, dict) or key not in value:
        return False
    child = value[key]
    if many:
        if not isinstance(child, list) or not child:
            return False
        return all(
            not (isinstance(item, dict) and "_truncated_items" in item)
            and _has_required(item, path[1:]) for item in child
        )
    return _has_required(child, path[1:])


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contains duplicate field names")
        result[key] = value
    return result


def _reject_non_json_constant(value: str) -> None:
    raise ValueError("JSON contains a non-standard numeric constant")


def _prepare_values(
    value: Any,
    totals: Counter[str],
    extra_keys: frozenset[str] = frozenset(),
    literals: tuple[str, ...] = (),
    *,
    depth: int = 0,
) -> Any:
    if depth > MAX_JSON_NESTING:
        raise ValueError("JSON is nested too deeply")
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            if _sensitive_key(key, extra_keys):
                cleaned[key] = MASK
                totals["FIELDS"] += 1
            else:
                cleaned[key] = _prepare_values(
                    child, totals, extra_keys, literals, depth=depth + 1,
                )
        return cleaned
    if isinstance(value, list):
        return [
            _prepare_values(child, totals, extra_keys, literals, depth=depth + 1)
            for child in value
        ]
    if isinstance(value, str):
        result = redact_text(value)
        totals.update(result.counts)
        return _mask_literals(result.text, literals, totals)
    return value


def redact_sensitive_text(text: str, mask_literals: str | None = None) -> dict[str, Any]:
    source = _check_text(text, "text")
    literals = _read_literals(mask_literals)
    result = redact_text(source)
    counts = Counter(result.counts)
    cleaned = _mask_literals(result.text, literals, counts)
    if len(cleaned) > MAX_OUTPUT_CHARS:
        raise ValueError("Sanitized result exceeds output size limit")
    return {
        "text": cleaned,
        "changed": cleaned != source,
        "redaction_counts": dict(counts),
    }


def prepare_agent_json(
    json_text: str,
    max_string: int = 1000,
    max_items: int = 25,
    max_depth: int = 8,
    *,
    allowed_paths: str | None = None,
    required_paths: str | None = None,
    additional_secret_keys: str | None = None,
    mask_literals: str | None = None,
    block_on_truncation: bool = False,
) -> dict[str, Any]:
    source = _check_text(json_text, "json_text")
    string_limit = _limit(max_string, 1000, 100, 4000, "max_string")
    items_limit = _limit(max_items, 25, 1, 100, "max_items")
    depth_limit = _limit(max_depth, 8, 1, 16, "max_depth")
    allowed = _parse_paths(allowed_paths, "allowed_paths")
    required = _parse_paths(required_paths, "required_paths")
    extra_keys = _read_key_names(additional_secret_keys)
    literals = _read_literals(mask_literals)
    strict_truncation = _bool(block_on_truncation, False, "block_on_truncation")
    if allowed and any(not _path_covered(path, allowed) for path in required):
        raise ValueError("Every required path must be included in the allowed selection")

    try:
        parsed = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_json_constant,
        )
    except (json.JSONDecodeError, UnicodeError, RecursionError):
        raise ValueError("json_text must contain valid JSON within nesting limits") from None

    if allowed and not isinstance(parsed, dict):
        raise ValueError("allowed_paths requires a JSON object at the root")
    selected = _project(parsed, _selection_tree(allowed)) if allowed else parsed
    field_count = _count_fields(parsed) - _count_fields(selected)
    if field_count < 0:
        raise ValueError("Failed to prepare allowed fields")

    redactions: Counter[str] = Counter()
    prepared = _prepare_values(selected, redactions, extra_keys, literals)
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

    truncated = any((
        stats.truncated_lists, stats.truncated_strings, stats.max_depth_hits,
    ))
    missing = [
        ".".join(path) for path in required
        if not _has_required(result, path)
    ]
    reasons: list[str] = []
    if not allowed:
        reasons.append("no_allowlist_configured")
    if allowed and not _has_real_selection(result):
        reasons.append("no_selected_fields")
    if missing:
        reasons.append("required_fields_missing")
    if truncated:
        reasons.append("content_truncated")
    if redactions:
        reasons.append("patterns_masked")

    blocked = bool(
        missing or (allowed and not _has_real_selection(result))
        or (strict_truncation and truncated)
    )
    status = "block" if blocked else ("review" if reasons else "pass")
    output = "" if blocked else serialized
    return {
        "json_text": output,
        "policy_status": status,
        "policy_reasons": reasons,
        "missing_required_paths": missing,
        "may_auto_continue": status == "pass",
        "changed": output != source,
        "input_characters": len(source),
        "output_characters": len(output),
        "characters_removed": max(0, len(source) - len(output)),
        "fields_excluded": field_count,
        "redaction_counts": dict(redactions),
        "compaction": asdict(stats),
    }
