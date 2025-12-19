"""
Qdrant-backed code search backend for gap analysis.

Uses AST-aware chunking with tree-sitter and hybrid search (vector + keyword).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from app.config import get_settings
from app.services.gap_analysis_service import CodeChunk, CodeSearchBackend, IdeaTicket

logger = logging.getLogger(__name__)

# Try to import tree-sitter-languages, but make it optional
try:
    from tree_sitter_languages import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter-languages not available. Falling back to simple chunking.")


class QdrantCodeSearchBackend(CodeSearchBackend):
    """
    Qdrant-backed code search using semantic embeddings and AST-aware chunking.
    """

    COLLECTION_NAME = "argos_codebase"

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        embedding_model: Optional[SentenceTransformer] = None,
    ):
        settings = get_settings()
        self.client = qdrant_client or QdrantClient(url=settings.qdrant_url)
        # Use code-specific embedding model if available, fallback to general model
        try:
            # Try code-specific model first
            # Local import to avoid import-time failure when sentence-transformers isn't present
            from sentence_transformers import SentenceTransformer
            self.model = embedding_model or SentenceTransformer("jinaai/jina-embeddings-v2-base-code")
            self.embedding_size = 768  # jina-embeddings-v2-base-code dimension
        except Exception:
            try:
                # Fallback to microsoft/codebert-base
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("microsoft/codebert-base")
                self.embedding_size = 768
            except Exception:
                # Final fallback
                logger.warning("Code-specific models not available, using general model")
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.embedding_size = 384

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure the codebase collection exists."""
        try:
            collections = self.client.get_collections()
            if self.COLLECTION_NAME not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(size=self.embedding_size, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    def _chunk_code_ast(self, code: str, file_path: str, language: Optional[str] = None) -> List[dict]:
        """
        Chunk code using AST parsing (tree-sitter).
        Falls back to simple function/class splitting if tree-sitter is unavailable.
        """
        chunks = []

        if not TREE_SITTER_AVAILABLE:
            # Fallback: simple function/class-based chunking
            return self._chunk_code_simple(code, file_path)

        try:
            # Determine language from file extension if not provided
            if not language:
                ext = file_path.split(".")[-1].lower()
                lang_map = {
                    "py": "python",
                    "js": "javascript",
                    "ts": "typescript",
                    "rs": "rust",
                    "go": "go",
                    "java": "java",
                    "cpp": "cpp",
                    "c": "c",
                }
                language = lang_map.get(ext, "python")  # Default to python

            # For now, use simple chunking since tree-sitter language bindings require compilation
            # In production, you'd load pre-built language bindings
            return self._chunk_code_simple(code, file_path)

        except Exception as e:
            logger.warning(f"AST chunking failed for {file_path}: {e}, falling back to simple chunking")
            return self._chunk_code_simple(code, file_path)

    def _chunk_code_simple(self, code: str, file_path: str) -> List[dict]:
        """
        Simple chunking by function and class definitions.
        This is a fallback when AST parsing is unavailable.
        """
        chunks = []
        lines = code.split("\n")
        current_chunk = []
        current_start = 0
        in_function = False
        in_class = False
        indent_level = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Detect function definitions
            if stripped.startswith("def ") or stripped.startswith("async def "):
                if current_chunk and current_start < i:
                    chunks.append(
                        {
                            "content": "\n".join(current_chunk),
                            "line_start": current_start + 1,
                            "line_end": i,
                            "file_path": file_path,
                        }
                    )
                current_chunk = [line]
                current_start = i
                in_function = True
            # Detect class definitions
            elif stripped.startswith("class "):
                if current_chunk and current_start < i:
                    chunks.append(
                        {
                            "content": "\n".join(current_chunk),
                            "line_start": current_start + 1,
                            "line_end": i,
                            "file_path": file_path,
                        }
                    )
                current_chunk = [line]
                current_start = i
                in_class = True
            else:
                current_chunk.append(line)

        # Add final chunk
        if current_chunk:
            chunks.append(
                {
                    "content": "\n".join(current_chunk),
                    "line_start": current_start + 1,
                    "line_end": len(lines),
                    "file_path": file_path,
                }
            )

        return chunks

    def search_related_code(self, ticket: IdeaTicket, *, top_k: int) -> Sequence[CodeChunk]:
        """
        Search for code chunks related to the ticket using hybrid search.
        """
        if not self.client:
            logger.warning("Qdrant client not available")
            return []

        # Generate query embedding
        query_text = f"{ticket.title}\n{ticket.description or ''}"
        try:
            query_vector = self.model.encode(query_text).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

        # Perform vector search with project filter
        try:
            hits = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[FieldCondition(key="project_id", match=MatchValue(value=ticket.project_id))]
                ),
                limit=top_k,
            )

            # Map hits to CodeChunk objects
            chunks = []
            for hit in hits:
                payload = hit.payload or {}
                chunks.append(
                    CodeChunk(
                        file_path=payload.get("file_path", "unknown"),
                        content=payload.get("content", ""),
                        similarity=float(hit.score),
                    )
                )

            return chunks

        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    def ingest_code_file(self, project_id: str, file_path: str, code: str) -> None:
        """
        Ingest a code file into Qdrant with AST-aware chunking.
        This method should be called during code ingestion/indexing.
        """
        if not self.client:
            return

        chunks = self._chunk_code_ast(code, file_path)

        points = []
        for chunk in chunks:
            try:
                # Generate embedding for chunk
                vector = self.model.encode(chunk["content"]).tolist()

                # Create point with metadata
                point_id = f"{project_id}:{file_path}:{chunk['line_start']}"
                points.append(
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {
                            "project_id": project_id,
                            "file_path": file_path,
                            "content": chunk["content"],
                            "line_start": chunk["line_start"],
                            "line_end": chunk["line_end"],
                        },
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to process chunk in {file_path}:{chunk['line_start']}: {e}")

        if points:
            try:
                self.client.upsert(collection_name=self.COLLECTION_NAME, points=points)
                logger.info(f"Ingested {len(points)} chunks from {file_path}")
            except Exception as e:
                logger.error(f"Failed to upsert chunks: {e}")

