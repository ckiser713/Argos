from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Mapping, Optional, Sequence

from app.domain.project_intel import (
    EmbeddingVector,
    IdeaCandidate,
    IdeaCluster,
    IdeaTicket,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Adjust this import to your actual ChatSegment location.
    # Only used for type checking; no runtime dependency.
    from app.domain.chat import ChatSegment  # pragma: no cover


# Optional planner + embedding clients.
try:  # pragma: no cover - optional dependency
    from app.services.planner_client import planner_client
except ImportError:  # pragma: no cover - degrade gracefully
    planner_client = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from app.services.embedding_client import embedding_client
except ImportError:  # pragma: no cover
    embedding_client = None  # type: ignore[assignment]


# ---- helpers ----


def _stable_id(namespace: str, parts: Sequence[str]) -> str:
    """
    Deterministic short ID based on namespace + ordered parts.
    """
    joined = "|".join([namespace, *parts])
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return digest[:16]


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _cosine_similarity(a: EmbeddingVector, b: EmbeddingVector) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = 0.0
    sum_sq_a = 0.0
    sum_sq_b = 0.0
    for x, y in zip(a, b):
        num += x * y
        sum_sq_a += x * x
        sum_sq_b += y * y
    if sum_sq_a <= 0.0 or sum_sq_b <= 0.0:
        return 0.0
    from math import sqrt

    return num / (sqrt(sum_sq_a) * sqrt(sum_sq_b))


def _get_embedding(text: str) -> Optional[EmbeddingVector]:
    """
    Use your embedding client if present; otherwise return None.
    """
    if embedding_client is None:  # pragma: no cover - runtime fallback
        logger.debug(
            "project_intel.embedding_client_missing",
            extra={"reason": "no_embedding_client"},
        )
        return None

    # We assume embedding_client has a simple synchronous interface.
    # Adapt this to your actual implementation.
    try:
        return embedding_client.embed_text(text)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("project_intel.embedding_failed", extra={"error": str(exc)})
        return None


# ---- extraction ----


@dataclass
class _HeuristicMatch:
    score: float
    labels: List[str]


# Simple keyword heuristics; you can refine this over time.
_HEURISTIC_RULES: Dict[str, List[str]] = {
    "feature": [
        "we should add",
        "new feature",
        "support for",
        "it would be nice if",
    ],
    "refactor": ["refactor", "cleanup", "technical debt", "rewrite", "restructure"],
    "experiment": [
        "let's try",
        "experiment",
        "spike",
        "prototype",
        "mvp",
    ],
    "bug": ["bug", "broken", "doesn't work", "fails when"],
    "ops": ["alert", "monitoring", "observability", "deployment", "runbook"],
}


def _apply_heuristics(text: str) -> Optional[_HeuristicMatch]:
    text_lower = text.lower()
    labels: List[str] = []
    score = 0.0

    for label, phrases in _HEURISTIC_RULES.items():
        for phrase in phrases:
            if phrase in text_lower:
                labels.append(label)
                score += 0.2

    # Generic patterns for TODO / future work.
    generic_triggers = [
        "we should",
        "i want to build",
        "i want to add",
        "next step",
        "todo:",
        "to-do:",
        "future work",
        "roadmap",
    ]
    for phrase in generic_triggers:
        if phrase in text_lower:
            score += 0.2

    if score == 0.0:
        return None

    # Clamp score to [0, 1].
    score = min(score, 1.0)
    return _HeuristicMatch(score=score, labels=sorted(set(labels)))


def extract_idea_candidates_from_segments(
    segments: List["ChatSegment"],
) -> List[IdeaCandidate]:
    """
    Use heuristics to generate initial IdeaCandidates from ChatSegments,
    then optionally refine / re-label via the planner LLM if configured.

    Determinism:
      - Segments are processed in deterministic order (by segment_id as string).
      - IDs are derived via stable hashes.
    """
    logger.info(
        "project_intel.extract_idea_candidates.start",
        extra={"segment_count": len(segments)},
    )

    # Sort deterministically by segment id (or timestamp if you prefer).
    # We assume ChatSegment has "id" and "text" attributes and optional project_id/chat_id.
    sorted_segments = sorted(segments, key=lambda s: str(getattr(s, "id", "")))

    candidates: List[IdeaCandidate] = []

    for seg in sorted_segments:
        text = _normalize_text(getattr(seg, "text", ""))
        if not text:
            continue

        heuristic = _apply_heuristics(text)
        if not heuristic:
            continue

        # Title: first ~12 words; summary: first ~40 words.
        words = text.split()
        title = " ".join(words[:12])
        summary = " ".join(words[:40])

        project_id = getattr(seg, "project_id", None)
        segment_id = str(getattr(seg, "id", ""))
        chat_id = str(getattr(seg, "chat_id", ""))

        cand_id = _stable_id("idea_candidate", [segment_id, title.lower()])

        candidate = IdeaCandidate(
            id=cand_id,
            segment_id=segment_id,
            project_id=project_id,
            title=title,
            summary=summary,
            confidence=heuristic.score,
            labels=heuristic.labels,
            source_chat_ids=[chat_id] if chat_id else [],
        )
        candidates.append(candidate)

    logger.info(
        "project_intel.extract_idea_candidates.heuristics_done",
        extra={"candidate_count": len(candidates)},
    )

    # Optional planner refinement.
    if planner_client is not None and candidates:
        try:  # pragma: no cover - depends on external client
            logger.info(
                "project_intel.extract_idea_candidates.planner_call",
                extra={"candidate_count": len(candidates)},
            )
            refined = planner_client.refine_idea_candidates(
                segments=sorted_segments,
                candidates=candidates,
            )
            # Expect the planner to return the same IDs; fall back to original on mismatch.
            ids_original = {c.id for c in candidates}
            ids_refined = {c.id for c in refined}
            if ids_original == ids_refined:
                candidates = sorted(refined, key=lambda c: c.id)
                logger.info(
                    "project_intel.extract_idea_candidates.planner_success",
                    extra={"candidate_count": len(candidates)},
                )
            else:
                logger.warning(
                    "project_intel.extract_idea_candidates.planner_id_mismatch",
                    extra={
                        "original_count": len(ids_original),
                        "refined_count": len(ids_refined),
                    },
                )
        except Exception as exc:
            logger.exception(
                "project_intel.extract_idea_candidates.planner_error",
                extra={"error": str(exc)},
            )

    return candidates

# Clustering + ticket promotion
def cluster_ideas(candidates: List[IdeaCandidate]) -> List[IdeaCluster]:
    """
    Cluster IdeaCandidates using embeddings + a simple greedy cosine clustering.

    - If embeddings are available, we use them.
    - If embeddings are unavailable, we fall back to label-based clustering.
    """
    logger.info(
        "project_intel.cluster_ideas.start",
        extra={"candidate_count": len(candidates)},
    )
    if not candidates:
        return []

    # Compute embeddings (when available)
    embeddings: Dict[str, EmbeddingVector] = {}
    for c in candidates:
        emb_text = f"{c.title}. {c.summary}"
        emb = _get_embedding(emb_text)
        if emb is not None:
            embeddings[c.id] = emb

    use_embeddings = len(embeddings) == len(candidates)

    clusters: List[IdeaCluster] = []

    if use_embeddings:
        logger.info(
            "project_intel.cluster_ideas.mode_embeddings",
            extra={"candidate_count": len(candidates)},
        )
        similarity_threshold = 0.78  # tweak as needed

        for cand in sorted(candidates, key=lambda c: c.id):
            emb = embeddings[cand.id]
            best_cluster: Optional[IdeaCluster] = None
            best_sim = 0.0

            for cl in clusters:
                if cl.centroid_embedding is None:
                    continue
                sim = _cosine_similarity(emb, cl.centroid_embedding)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = cl

            if best_cluster is None or best_sim < similarity_threshold:
                # New cluster
                cluster_id = _stable_id("idea_cluster", [cand.project_id or "", cand.id])
                new_cluster = IdeaCluster(
                    id=cluster_id,
                    project_id=cand.project_id,
                    name=cand.title,
                    idea_ids=[cand.id],
                    centroid_embedding=emb,
                )
                clusters.append(new_cluster)
            else:
                # Assign to best cluster and update centroid
                best_cluster.idea_ids.append(cand.id)
                # Recompute centroid
                ids = best_cluster.idea_ids
                vecs = [embeddings[i] for i in ids if i in embeddings]
                if vecs:
                    dim = len(vecs[0])
                    centroid = [0.0] * dim
                    for v in vecs:
                        for i, x in enumerate(v):
                            centroid[i] += x
                    n = float(len(vecs))
                    best_cluster.centroid_embedding = [x / n for x in centroid]
    else:
        # Fallback: labels-based clustering (deterministic, no embeddings).
        logger.info(
            "project_intel.cluster_ideas.mode_labels",
            extra={"candidate_count": len(candidates)},
        )
        # Group by normalized labels key.
        groups: Dict[str, List[IdeaCandidate]] = {}
        for c in candidates:
            key_labels = tuple(sorted(set(c.labels))) or ("unlabeled",)
            key = "|".join(key_labels)
            groups.setdefault(key, []).append(c)

        for key, group in sorted(groups.items(), key=lambda kv: kv[0]):
            # Use the highest-confidence candidate as cluster name.
            top = sorted(group, key=lambda c: (-c.confidence, c.id))[0]
            cluster_id = _stable_id(
                "idea_cluster", [top.project_id or "", key, top.id]
            )
            clusters.append(
                IdeaCluster(
                    id=cluster_id,
                    project_id=top.project_id,
                    name=top.title,
                    idea_ids=[c.id for c in sorted(group, key=lambda c: c.id)],
                    centroid_embedding=None,
                )
            )

    logger.info(
        "project_intel.cluster_ideas.done",
        extra={
            "cluster_count": len(clusters),
            "candidate_count": len(candidates),
        },
    )
    return clusters

def promote_clusters_to_tickets(
    clusters: List[IdeaCluster],
    candidate_lookup: Optional[Mapping[str, IdeaCandidate]] = None,
) -> List[IdeaTicket]:
    """
    Turn clusters into promotable IdeaTickets.

    - If candidate_lookup is provided, we use it to generate richer titles/descriptions.
    - Optionally uses planner_client to refine titles/descriptions.
    """
    logger.info(
        "project_intel.promote_clusters_to_tickets.start",
        extra={"cluster_count": len(clusters)},
    )
    if not clusters:
        return []

    tickets: List[IdeaTicket] = []

    for cl in sorted(clusters, key=lambda c: c.id):
        project_id = cl.project_id
        ideas: List[IdeaCandidate] = []
        if candidate_lookup is not None:
            for idea_id in cl.idea_ids:
                cand = candidate_lookup.get(idea_id)
                if cand is not None:
                    ideas.append(cand)

        if ideas:
            # Simple heuristic: use the "best" idea as base title.
            best = sorted(ideas, key=lambda c: (-c.confidence, c.id))[0]
            title = best.title
            summaries = [c.summary for c in ideas]
            description = "Cluster of related ideas:\n\n" + "\n\n".join(
                f"- {s}" for s in summaries
            )
        else:
            title = cl.name
            description = (
                "Ticket generated from idea cluster with "
                f"{len(cl.idea_ids)} related ideas."
            )

        ticket_id = _stable_id("idea_ticket", [project_id or "", cl.id])

        ticket = IdeaTicket(
            id=ticket_id,
            project_id=project_id,
            cluster_id=cl.id,
            title=title,
            description=description,
            status="candidate",
            priority="medium",
            origin_idea_ids=list(cl.idea_ids),
        )
        tickets.append(ticket)

    # Optional: planner refinement of titles/descriptions.
    if planner_client is not None and tickets:
        try:  # pragma: no cover - external integration
            logger.info(
                "project_intel.promote_clusters_to_tickets.planner_call",
                extra={"ticket_count": len(tickets)},
            )
            refined = planner_client.refine_idea_tickets(
                clusters=clusters,
                tickets=tickets,
            )
            ids_original = {t.id for t in tickets}
            ids_refined = {t.id for t in refined}
            if ids_original == ids_refined:
                tickets = sorted(refined, key=lambda t: t.id)
            else:
                logger.warning(
                    "project_intel.promote_clusters_to_tickets.planner_id_mismatch",
                    extra={
                        "original_count": len(ids_original),
                        "refined_count": len(ids_refined),
                    },
                )
        except Exception as exc:
            logger.exception(
                "project_intel.promote_clusters_to_tickets.planner_error",
                extra={"error": str(exc)},
            )

    logger.info(
        "project_intel.promote_clusters_to_tickets.done",
        extra={"ticket_count": len(tickets)},
    )
    return tickets
