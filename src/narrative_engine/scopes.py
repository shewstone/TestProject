"""Scope registry and alias resolver (T5, docs/tickets/T5-scope-registry.md).

The scope partition is composition's stage-1 hard filter (design doc
Sec 6.2 stage 6): inconsistent raw scope labels from extraction ("US" vs
"United States") silently fragment arc instances. This module resolves raw
strings against a versioned alias registry.

Resolution is exact-alias-only, deliberately: a WRONG scope silently
poisons the composition partition, while an UNRESOLVED scope falls into
the v0.7 unscoped-singleton path, which is visible and safe. Same
asymmetry logic as the evidence floor — absence of evidence must never
behave like evidence.

The registry itself is versioned data, not ontology (Sec 9: scope
boundaries are contested claims). Registry changes are data changes plus a
version bump in scope_registry.json; no code change.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from typing import Dict, List, Optional

from narrative_engine.logging_config import get_logger
from narrative_engine.models import Scope

logger = get_logger(__name__)

_REGISTRY_PACKAGE = "narrative_engine.data"
_REGISTRY_RESOURCE = "scope_registry.json"

_ARTICLE_PREFIXES = ("the ",)


def _normalize(raw: str) -> str:
    """Casefold, strip punctuation/articles, collapse whitespace."""
    text = raw.casefold().strip()
    for prefix in _ARTICLE_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


class ScopeRegistry:
    """In-memory registry: id -> Scope, normalized alias -> id."""

    def __init__(self, version: str, scopes: List[Scope]):
        self.version = version
        self._by_id: Dict[str, Scope] = {s.id: s for s in scopes}
        self._alias_to_id: Dict[str, str] = {}
        for scope in scopes:
            for alias in [scope.id, scope.name, *scope.aliases]:
                key = _normalize(alias)
                existing = self._alias_to_id.get(key)
                if existing and existing != scope.id:
                    raise ValueError(
                        f"Alias collision in scope registry: {alias!r} maps to "
                        f"both {existing!r} and {scope.id!r}"
                    )
                self._alias_to_id[key] = scope.id

    @classmethod
    def load(cls) -> "ScopeRegistry":
        raw = resources.files(_REGISTRY_PACKAGE).joinpath(_REGISTRY_RESOURCE).read_text()
        data = json.loads(raw)
        scopes = [Scope(**entry) for entry in data["scopes"]]
        return cls(version=data["version"], scopes=scopes)

    def resolve(self, raw: Optional[str]) -> Optional[str]:
        """Resolve a raw scope string to a registry scope id, or None.

        None means "unresolved": callers must keep the episode on the
        visible unscoped/raw-string path, never guess. Unresolved strings
        are logged — they are the promotion queue for new aliases.
        """
        if not raw:
            return None
        scope_id = self._alias_to_id.get(_normalize(raw))
        if scope_id is None:
            logger.info("scope_unresolved", raw=raw)
        return scope_id

    def get(self, scope_id: str) -> Optional[Scope]:
        return self._by_id.get(scope_id)

    def all(self) -> List[Scope]:
        return list(self._by_id.values())


@lru_cache(maxsize=1)
def get_registry() -> ScopeRegistry:
    return ScopeRegistry.load()


def resolve_scope(raw: Optional[str]) -> Optional[str]:
    """Module-level convenience wrapper over the packaged registry."""
    return get_registry().resolve(raw)


def scope_registry_version() -> str:
    return get_registry().version
