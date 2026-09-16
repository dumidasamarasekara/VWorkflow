"""Shared merge helpers for DMAD config and customization resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

_KEY_FIELDS = ("code", "id")


def _list_key_field(items: list[Any]) -> str | None:
    """Return the identity field if every item is a dict sharing one of code/id."""
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    for field in _KEY_FIELDS:
        if all(field in item for item in items):
            return field
    return None


def _merge_keyed_lists(base: list[Any], override: list[Any], field: str) -> list[Any]:
    merged = [dict(item) for item in base]
    index = {item[field]: position for position, item in enumerate(merged)}
    for item in override:
        key = item[field]
        if key in index:
            merged[index[key]] = structural_merge(merged[index[key]], item)
        else:
            index[key] = len(merged)
            merged.append(dict(item))
    return merged


def structural_merge(base: Any, override: Any) -> Any:
    """Merge `override` onto `base` using DMAD layering rules."""
    if override is None:
        return base

    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = structural_merge(merged.get(key), value)
        return merged

    if isinstance(base, list) and isinstance(override, list):
        field = _list_key_field(base) or _list_key_field(override)
        if field and all(
            isinstance(item, dict) and field in item for item in [*base, *override]
        ):
            return _merge_keyed_lists(base, override, field)
        return [*base, *override]

    return override


def load_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file, returning an empty dict when it is missing."""
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def merge_layers(paths: list[Path]) -> dict[str, Any]:
    """Merge TOML layers in order, skipping files that do not exist."""
    result: dict[str, Any] = {}
    for path in paths:
        result = structural_merge(result, load_toml(path))
    return result


def get_key(data: dict[str, Any], dotted_key: str | None) -> Any:
    """Resolve a dotted path such as `runtime.user_name`."""
    if not dotted_key:
        return data
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def agent_layers(project_root: Path, agent_id: str) -> list[Path]:
    """Customization layers for an agent: base -> team -> personal."""
    dmad = project_root / "_dmad"
    return [
        dmad / "agents" / agent_id / "customize.toml",
        dmad / "custom" / f"{agent_id}.toml",
        dmad / "custom" / f"{agent_id}.user.toml",
    ]
