"""Vector embedding generation for semantic search."""

from __future__ import annotations

from typing import List, Optional

import structlog
from sentence_transformers import SentenceTransformer

from narrative_engine.models import Episode
from narrative_engine.retrieval.epochs import EMBEDDING_MODEL_NAME

logger = structlog.get_logger()


class EmbeddingGenerator:
    """Generate vector embeddings for episodes using sentence-transformers."""

    # Pinned model (Sec 6.3); single source of truth lives in epochs.py so
    # epoch identifiers can't drift from the model actually used.
    DEFAULT_MODEL = EMBEDDING_MODEL_NAME

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model: Optional[SentenceTransformer] = None
        self.logger = structlog.get_logger()

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            self.logger.info("Loading embedding model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self.logger.info(
                "Model loaded",
                embedding_dim=self._model.get_sentence_embedding_dimension(),
            )
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Get the dimensionality of embeddings."""
        return self.model.get_sentence_embedding_dimension()

    def generate(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (more efficient)."""
        embeddings = self.model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [e.tolist() for e in embeddings]

    def render_structural_template(self, episode: Episode) -> str:
        """Deterministically render the episode's abstract narrative shape
        (design doc Sec 3.3): arc type, phase, actor roles (not names),
        mechanism tags, and the sequence of conditions/mechanics/tension --
        never raw title/summary text, actor names, location, or dates.

        This is what makes the structural embedding place/date-blind (so
        Athens-Sparta can embed near Wilhelmine Germany-Britain): title and
        summary are natural-language prose anchored to the specific
        happening, and actor names are proper nouns, so including either
        re-introduces the exact identity signal the structural/surface
        split (Sec 3.3a) exists to keep separate.

        Outcome fields (resolution, consequences) are ALWAYS excluded, for
        two reasons. (1) Query/corpus symmetry: a present-day query episode
        has resolution=None by definition, so embedding outcomes for corpus
        episodes but not queries makes every retrieval score systematically
        biased by a field only one side has. (2) Leakage: retrieval is
        "given the situation so far, what followed?" -- if the embedding
        encodes how the story ended, backtests partially retrieve analogs
        BY their endings, which is the masking failure Sec 6.6 exists to
        prevent. Outcomes still reach theses via the analogs' stored
        resolution/consequences fields after retrieval (Sec 6.5 step 5);
        they just never enter the similarity signal.
        """
        lines: List[str] = []

        if episode.arc_type:
            lines.append(f"Arc: {episode.arc_type.value}")

        if episode.arc_phase:
            lines.append(f"Phase: {episode.arc_phase.value}")

        if episode.actors:
            # Controlled-vocabulary tokens ONLY (T2): canonical_role where
            # the fit floor was cleared, one shared unresolved token where it
            # wasn't. The free-text role is prose ("President", "J.P.
            # Morgan's bank") and must never reach the analogy signal.
            from narrative_engine.extraction.roles import UNRESOLVED_ACTOR_TOKEN

            seen = set()
            roles = []
            for actor in episode.actors:
                token = actor.canonical_role or UNRESOLVED_ACTOR_TOKEN
                if token not in seen:
                    seen.add(token)
                    roles.append(token)
            lines.append(f"Actor roles: {', '.join(roles)}")

        if episode.mechanism_tags:
            # Sec 3.3 template's MECHANISMS line: controlled-vocabulary
            # structural drivers, serialized in tag order.
            lines.append(
                f"Mechanisms: {', '.join(tag.value for tag in episode.mechanism_tags)}"
            )

        scrub = self._identity_scrubber(episode)

        if episode.initiating_conditions:
            lines.append("Initiating conditions:")
            lines.extend(f"- {scrub(c)}" for c in episode.initiating_conditions)

        if episode.escalation_mechanics:
            lines.append("Escalation mechanics:")
            lines.extend(f"- {scrub(m)}" for m in episode.escalation_mechanics)

        if episode.tension:
            lines.append(f"Tension: {scrub(episode.tension)}")

        return "\n".join(lines)

    def _identity_scrubber(self, episode: Episode):
        """Build a deterministic scrub function for this episode's free-text
        lines (T2): actor names -> their role token, the episode's
        place/scope names -> <PLACE>, years and month names -> <DATE>.

        The render is deterministic code, not an LLM (Sec 6.2 stage 3), so
        the place/date-blind guarantee is enforced HERE, not hoped for in
        the extraction prompt. Replacement, not deletion: a resolved actor
        mention keeps its structural meaning under its role token.
        """
        import re

        from narrative_engine.extraction.roles import UNRESOLVED_ACTOR_TOKEN

        replacements: List[tuple] = []

        for actor in episode.actors:
            if actor.name:
                token = actor.canonical_role or UNRESOLVED_ACTOR_TOKEN
                replacements.append((actor.name, token))

        place_names: List[str] = []
        if episode.location:
            place_names.append(episode.location)
        if episode.scope_id:
            from narrative_engine.scopes import get_registry, resolve_scope

            scope_id = resolve_scope(episode.scope_id) or None
            scope = get_registry().get(scope_id) if scope_id else None
            place_names.append(episode.scope_id)
            if scope:
                place_names.extend([scope.name, *scope.aliases])
        for place in place_names:
            replacements.append((place, "<PLACE>"))

        # Longest-first so "United States of America" wins over "America".
        # Lookaround word anchors, not \b: aliases like "U.S." end in
        # punctuation where \b would fail, and unanchored matching rewrites
        # substrings ("us" inside "Trust").
        replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

        def _compile(source: str, target: str):
            # Place replacements absorb a preceding article so "the United
            # States" and "Austria-Hungary" both normalize to bare <PLACE> --
            # article variance is identity residue too.
            article = r"(?:the\s+)?" if target == "<PLACE>" else ""
            return re.compile(
                rf"(?<!\w){article}{re.escape(source)}(?!\w)", re.IGNORECASE
            )

        compiled = [
            (_compile(source, target), target)
            for source, target in replacements
            if source
        ]

        year_pattern = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})s?\b")
        month_pattern = re.compile(
            r"\b(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\b",
            re.IGNORECASE,
        )

        def scrub(text: str) -> str:
            for pattern, target in compiled:
                text = pattern.sub(target, text)
            text = year_pattern.sub("<DATE>", text)
            text = month_pattern.sub("<DATE>", text)
            return text

        return scrub

    def generate_structural_embedding(self, episode: Episode) -> List[float]:
        """Generate the structural embedding: analogy signal, NOT identity.

        Embeds render_structural_template's place/date-blind rendering of
        the episode's abstract narrative structure. This is what makes
        cross-domain analogy matching work (Athens-Sparta embeds near
        Germany-Britain). That same place/date-blindness makes it WRONG for
        identity resolution ("is this the same happening?") -- use
        generate_surface_embedding for that (design doc Sec 3.3a).

        Consumers: analog retrieval (AnalogRetrievalEngine), discovery
        clustering. Never: SAME_EVENT_AS resolution, arc composition.
        """
        return self.generate(self.render_structural_template(episode))

    def generate_surface_embedding(self, episode: Episode) -> List[float]:
        """Generate the surface embedding: identity signal, NOT analogy.

        Raw title + summary text only -- no role substitution, no arc/phase
        labels. Captures "is this the same happening?" (two sources
        describing the same crash), not "is this the same shape?" (design
        doc Sec 3.3a).

        Consumers: SAME_EVENT_AS resolution, arc composition. Never: analog
        retrieval, discovery clustering.
        """
        text = f"{episode.title}\n{episode.summary}"
        return self.generate(text)

    def generate_for_query(self, query: str) -> List[float]:
        """Generate embedding for a search query.

        Queries are often shorter and less structured than episodes,
        so we use them as-is but could enhance with query expansion.
        """
        return self.generate(query)

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        import numpy as np

        v1 = np.array(embedding1)
        v2 = np.array(embedding2)

        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def compute_similarities(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
    ) -> List[float]:
        """Compute similarities between query and multiple candidates."""
        return [self.similarity(query_embedding, cand) for cand in candidate_embeddings]


class EmbeddingCache:
    """Simple in-memory cache for embeddings (production: use Redis)."""

    def __init__(self) -> None:
        self._cache: dict = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        self._cache[key] = embedding

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "size": len(self._cache),
        }

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
