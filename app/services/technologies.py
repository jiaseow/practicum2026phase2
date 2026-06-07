from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


TECH_DB_PATH = Path(__file__).resolve().parents[1] / "lib" / "technologies.json"


@dataclass(frozen=True)
class Technology:
    key: str
    name: str
    category: str
    confidence_tier: str
    aliases: tuple[str, ...]


@lru_cache
def load_technologies() -> dict[str, Technology]:
    with TECH_DB_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    return {
        key: Technology(
            key=key,
            name=value["name"],
            category=value["category"],
            confidence_tier=value.get("confidence_tier", "medium"),
            aliases=tuple(value.get("aliases", [key])),
        )
        for key, value in raw.items()
    }


@lru_cache
def alias_index() -> dict[str, Technology]:
    index: dict[str, Technology] = {}
    for tech in load_technologies().values():
        index[tech.key.lower()] = tech
        index[tech.name.lower()] = tech
        for alias in tech.aliases:
            index[alias.lower()] = tech
    return index


def match_technology(name: str) -> Technology | None:
    normalized = normalize_dependency_name(name)
    index = alias_index()
    return index.get(normalized) or index.get(name.lower())


def normalize_dependency_name(name: str) -> str:
    value = name.strip().lower()
    if value.startswith("@"):
        parts = value.split("/")
        return "/".join(parts[:2]) if len(parts) > 1 else value
    return value.split("/")[0].split(".")[0] if "." in value and not value.startswith("next.") else value.split("/")[0]
