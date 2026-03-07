"""BrainMVP retriever — fetches evidence from brain-mvp's RAG API."""

import logging
from typing import Any, Optional
from uuid import uuid4

import httpx

from ..models.core import EvidenceItem, Provenance
from ..models.types import SourceType
from ..config.loader import config_loader

logger = logging.getLogger("queryreactor.services.brain_retriever")


class BrainMVPRetriever:
    """Retriever that calls brain-mvp's POST /api/v1/chunks/search endpoint."""

    def __init__(self) -> None:
        config_loader.ensure_loaded()
        self._api_url: Optional[str] = (
            config_loader.get_env("BRAIN_MVP_API_URL")
            or config_loader.get_config("brain_mvp.api_url")
        )
        self._top_k: int = int(config_loader.get_config("brain_mvp.top_k", 10))
        self._similarity_threshold: float = float(
            config_loader.get_config("brain_mvp.similarity_threshold", 0.0)
        )
        self._neighbor_window: int = int(
            config_loader.get_config("brain_mvp.neighbor_window", 1)
        )
        self._timeout_ms: int = int(
            config_loader.get_config("brain_mvp.timeout_ms", 5000)
        )

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        neighbor_window: Optional[int] = None,
        doc_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search brain-mvp for relevant chunks.

        Returns the ``hits`` list from the response, or [] on failure/misconfiguration.
        """
        if not self._api_url:
            logger.warning(
                "BRAIN_MVP_API_URL not configured — skipping brain-mvp retrieval"
            )
            return []

        payload: dict[str, Any] = {
            "query": query,
            "top_k": top_k if top_k is not None else self._top_k,
            "similarity_threshold": (
                similarity_threshold
                if similarity_threshold is not None
                else self._similarity_threshold
            ),
            "neighbor_window": (
                neighbor_window if neighbor_window is not None else self._neighbor_window
            ),
        }
        if doc_filter:
            payload["doc_filter"] = doc_filter

        url = f"{self._api_url.rstrip('/')}/api/v1/chunks/search"
        timeout = self._timeout_ms / 1000.0

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("hits", [])
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "brain-mvp search returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
        except Exception as exc:
            logger.warning("brain-mvp search failed: %s", exc)

        return []

    def to_evidence_item(
        self,
        hit: dict[str, Any],
        workunit: Any,
        router_decision_id: str,
        retrieval_path: str = "P1",
    ) -> EvidenceItem:
        """Map a brain-mvp chunk hit to an EvidenceItem."""
        content = hit.get("enriched_content") or hit.get("original_content") or " "
        metadata = hit.get("metadata") or {}
        section_path = metadata.get("section_path", "")

        provenance = Provenance(
            source_type=SourceType.db,
            source_id=hit.get("doc_uuid", ""),
            doc_id=hit.get("doc_uuid", ""),
            chunk_id=hit.get("chunk_id", str(uuid4())),
            retrieval_path=retrieval_path,
            router_decision_id=router_decision_id,
        )

        return EvidenceItem(
            workunit_id=workunit.id,
            user_id=workunit.user_id,
            conversation_id=workunit.conversation_id,
            content=content,
            title=section_path or hit.get("doc_uuid", ""),
            section_title=section_path,
            score_raw=float(hit.get("score", 0.0)),
            provenance=provenance,
        )


# Module-level singleton
brain_retriever = BrainMVPRetriever()
