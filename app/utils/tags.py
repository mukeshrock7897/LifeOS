from __future__ import annotations

from typing import Iterable, Optional


def normalize_tags(value: Optional[str | Iterable[str]]) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        raw_items: Iterable[str] = value.replace(";", ",").split(",")
    else:
        raw_items = value

    cleaned: list[str] = []
    seen = set()
    for item in raw_items:
        tag = str(item).strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        cleaned.append(tag)
    return ",".join(cleaned)


def tags_to_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [tag for tag in (part.strip() for part in value.split(",")) if tag]


def merge_tags(existing: Optional[str], new_tags: Optional[str | Iterable[str]]) -> str:
    base = tags_to_list(existing or "")
    combined = base + tags_to_list(normalize_tags(new_tags))
    return normalize_tags(combined)


def remove_tags(existing: Optional[str], tags: Optional[str | Iterable[str]]) -> str:
    if not existing:
        return ""
    remove_set = set(tags_to_list(normalize_tags(tags)))
    remaining = [tag for tag in tags_to_list(existing) if tag not in remove_set]
    return normalize_tags(remaining)
