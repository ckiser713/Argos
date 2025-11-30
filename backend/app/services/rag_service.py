"""
RAG (Retrieval-Augmented Generation) service using Qdrant for vector storage and search.

Advanced features:
- Query rewriting and decomposition
- Multi-hop reasoning
- Citation tracking
- Source attribution
- Query history and refinement
- Context window management
- Hybrid search with re-ranking
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_community.vectorstores.qdrant import Qdrant
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.services.llm_service import generate_text, get_routed_llm_config
from app.services.qdrant_service import QdrantService, qdrant_service

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a citation to a source document."""
    document_id: str
    chunk_index: int
    content: str
    score: float
    metadata: Dict


@dataclass
class RAGQuery:
    """Represents a RAG query with history and context."""
    query: str
    project_id: str
    timestamp: datetime
    rewritten_queries: Optional[List[str]] = None
    citations: Optional[List[Citation]] = None
    refinement: Optional[str] = None


class RagService:
    """
    RAG service for document ingestion and semantic search.
    Uses QdrantService for vector operations with proper project scoping.
    
    Advanced features:
    - Query rewriting for better retrieval
    - Multi-hop reasoning for complex queries
    - Citation tracking and source attribution
    - Query refinement based on results
    - Context window management
    """

    def __init__(self):
        self.settings = get_settings()
        # Use QdrantService for all operations
        self.qdrant_service: QdrantService = qdrant_service
        # Query history per project (in-memory, could be persisted)
        self._query_history: Dict[str, List[RAGQuery]] = {}
        # Expose the RAGQuery dataclass on the instance for test compatibility
        self.RAGQuery = RAGQuery

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> List[Dict[str, str]]:
        """
        Chunk text with overlapping windows for better context preservation.
        Returns list of chunk dictionaries with content and index.
        """
        if not text:
            return []

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size
            chunk_content = text[start:end]

            chunks.append({
                "content": chunk_content,
                "chunk_index": chunk_index,
                "start_char": start,
                "end_char": end,
            })

            chunk_index += 1
            start = end - overlap  # Overlap for context

        return chunks

    def ingest_document(
        self,
        project_id: str,
        document_id: str,
        text: str,
        metadata: Optional[Dict] = None,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> int:
        """
        Ingest a document by chunking and storing in Qdrant.
        Returns number of chunks created.
        """
        if not text:
            logger.warning(f"Empty text provided for document {document_id}")
            return 0

        try:
            # Chunk the text
            chunks_data = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)

            # Prepare chunks for upsert
            chunks = []
            for chunk_data in chunks_data:
                chunk_id = f"{document_id}_chunk_{chunk_data['chunk_index']}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": chunk_data["content"],
                    "metadata": {
                        **(metadata or {}),
                        "project_id": project_id,
                        "document_id": document_id,
                        "created_at": datetime.now().isoformat(),
                        "chunk_index": chunk_data["chunk_index"],
                        "start_char": chunk_data["start_char"],
                        "end_char": chunk_data["end_char"],
                    },
                })

            # Upsert chunks using QdrantService
            upserted = self.qdrant_service.upsert_document_chunks(
                project_id=project_id,
                document_id=document_id,
                chunks=chunks,
                collection_type="documents",
            )

            logger.info(f"Ingested document {document_id} into project {project_id}: {upserted} chunks")
            # Also create a knowledge node for the document so that text-based
            # searches can find the document even when embedding models are not available.
            try:
                from app.services.knowledge_service import knowledge_service

                title = document_id
                summary = (text[:200] + "...") if len(text) > 200 else text
                try:
                    knowledge_service.create_node(project_id, {
                        "title": title,
                        "summary": summary,
                        "text": text,
                        "type": "document",
                        "tags": [],
                    })
                except Exception:
                    # If node already exists or creation fails, ignore
                    pass
            except Exception:
                pass
            return upserted

        except Exception as e:
            logger.error(f"Failed to ingest document {document_id}: {e}")
            return 0

    def rewrite_query(self, query: str, project_id: str) -> List[str]:
        """
        Rewrite a query into multiple search queries for better retrieval.
        Uses LLM to decompose complex queries and generate alternative phrasings.
        """
        try:
            prompt = f"""Rewrite the following search query into 2-3 alternative search queries that would help retrieve relevant information.
Each query should focus on a different aspect or use different terminology.

Original query: {query}

Return only a JSON array of query strings, no other text.
Example: ["query 1", "query 2", "query 3"]
"""
            
            response = generate_text(
                prompt=prompt,
                project_id=project_id,
                temperature=0.3,
            )
            
            # Try to parse JSON array from response
            import json
            import re
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*?\]', response.response, re.DOTALL)
            if json_match:
                queries = json.loads(json_match.group())
                return queries if isinstance(queries, list) else [query]
            
            # Fallback: return original query
            return [query]
            
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}, using original query")
            return [query]

    def search_with_rewriting(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None,
        use_rewriting: bool = True,
    ) -> Tuple[List[Dict], List[str]]:
        """
        Search with query rewriting for better retrieval.
        Returns (results, rewritten_queries).
        """
        rewritten_queries = [query]
        
        if use_rewriting:
            rewritten_queries = self.rewrite_query(query, project_id)
        
        # Search with each rewritten query and combine results
        all_results = []
        seen_chunk_ids = set()
        
        for rewritten_query in rewritten_queries:
            try:
                results = self.qdrant_service.search_documents(
                    project_id=project_id,
                    query=rewritten_query,
                    limit=limit * 2,  # Get more results per query
                    collection_type="documents",
                    document_id=document_id,
                )
                
                # Deduplicate by chunk_id
                for r in results:
                    chunk_id = f"{r.get('document_id')}_{r.get('chunk_index')}"
                    if chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(chunk_id)
                        all_results.append({
                            "content": r.get("content", ""),
                            "score": r["score"],
                            "document_id": r.get("document_id"),
                            "chunk_index": r.get("chunk_index"),
                            "metadata": r.get("metadata", {}),
                            "query_used": rewritten_query,
                        })
            except Exception as e:
                logger.warning(f"Search with rewritten query failed: {e}")
        
        # Sort by score and limit
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit], rewritten_queries

    def multi_hop_search(
        self,
        project_id: str,
        query: str,
        max_hops: int = 2,
        limit_per_hop: int = 3,
    ) -> Tuple[List[Dict], List[str]]:
        """
        Perform multi-hop reasoning: use initial results to refine the query.
        
        Args:
            project_id: Project ID
            query: Initial query
            max_hops: Maximum number of reasoning hops
            limit_per_hop: Results to retrieve per hop
            
        Returns:
            (final_results, reasoning_chain)
        """
        reasoning_chain = [query]
        current_results = []
        
        for hop in range(max_hops):
            # Search with current query
            if hop == 0:
                results, rewritten = self.search_with_rewriting(
                    project_id=project_id,
                    query=query,
                    limit=limit_per_hop,
                )
            else:
                # Use previous results to refine query
                context = "\n".join([
                    f"- {r['content'][:200]}..." 
                    for r in current_results[:3]
                ])
                
                refinement_prompt = f"""Based on the following search results, refine the query to find more specific information.

Original query: {query}

Search results so far:
{context}

Generate a refined query that builds on these results to find more specific or related information.
Return only the refined query, no explanation.
"""
                
                try:
                    refined_query = generate_text(
                        prompt=refinement_prompt,
                        project_id=project_id,
                        temperature=0.2,
                    ).response.strip()
                    
                    reasoning_chain.append(refined_query)
                    results, _ = self.search_with_rewriting(
                        project_id=project_id,
                        query=refined_query,
                        limit=limit_per_hop,
                        use_rewriting=False,
                    )
                except Exception as e:
                    logger.warning(f"Query refinement failed at hop {hop}: {e}")
                    break
            
            # Merge results, avoiding duplicates
            seen_chunk_ids = {f"{r['document_id']}_{r['chunk_index']}" for r in current_results}
            for r in results:
                chunk_id = f"{r['document_id']}_{r['chunk_index']}"
                if chunk_id not in seen_chunk_ids:
                    current_results.append(r)
                    seen_chunk_ids.add(chunk_id)
        
        # Sort by score
        current_results.sort(key=lambda x: x["score"], reverse=True)
        return current_results[:limit_per_hop * max_hops], reasoning_chain

    def search(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
        document_id: Optional[str] = None,
        use_advanced: bool = False,
        multi_hop: bool = False,
    ) -> Dict:
        """
        Enhanced search with optional advanced features.
        
        Args:
            project_id: Project ID
            query: Search query
            limit: Maximum results to return
            document_id: Optional document filter
            use_advanced: Enable query rewriting
            multi_hop: Enable multi-hop reasoning
            
        Returns:
            Dictionary with results, citations, and metadata
        """
        try:
            # Record query in history
            rag_query = RAGQuery(
                query=query,
                project_id=project_id,
                timestamp=datetime.now(),
            )
            
            if project_id not in self._query_history:
                self._query_history[project_id] = []
            self._query_history[project_id].append(rag_query)
            
            # Perform search
            if multi_hop:
                results, reasoning_chain = self.multi_hop_search(
                    project_id=project_id,
                    query=query,
                    max_hops=2,
                    limit_per_hop=limit // 2,
                )
                rag_query.rewritten_queries = reasoning_chain
            elif use_advanced:
                results, rewritten_queries = self.search_with_rewriting(
                    project_id=project_id,
                    query=query,
                    limit=limit,
                    document_id=document_id,
                )
                rag_query.rewritten_queries = rewritten_queries
            else:
                # Self-querying retriever
                metadata_field_info = [
                    AttributeInfo(
                        name="project_id",
                        description="The project ID",
                        type="string",
                    ),
                    AttributeInfo(
                        name="document_id",
                        description="The document ID",
                        type="string",
                    ),
                    AttributeInfo(
                        name="source",
                        description="The source of the document",
                        type="string",
                    ),
                    AttributeInfo(
                        name="created_at",
                        description="The creation time of the document",
                        type="string",
                    ),
                ]
                document_content_description = "Content of a document"
                base_url, model_name, backend, _ = get_routed_llm_config(query)
                
                # SelfQueryRetriever expects a LangChain-compatible ChatModel.
                # If routing suggests llama_cpp, fall back to the main OpenAI-compatible model.
                if backend == "llama_cpp":
                    base_url = self.settings.llm_base_url
                    model_name = self.settings.llm_model_name

                llm = ChatOpenAI(
                    model=model_name,
                    base_url=base_url,
                    api_key=self.settings.llm_api_key,
                    temperature=0,
                )

                embeddings = self.qdrant_service.embedding_models.get("default")
                if not embeddings:
                    raise ValueError("Default embedding model not found")

                vector_store = Qdrant(
                    client=self.qdrant_service.client,
                    collection_name=self.qdrant_service._get_collection_name(
                        project_id, "documents"
                    ),
                    embeddings=embeddings,
                )

                retriever = SelfQueryRetriever.from_llm(
                    llm,
                    vector_store,
                    document_content_description,
                    metadata_field_info,
                    verbose=True,
                )

                docs = retriever.get_relevant_documents(query)

                results = []
                for doc in docs:
                    results.append(
                        {
                            "content": doc.page_content,
                            "score": 1.0,  # Self-query doesn't provide a score
                            "document_id": doc.metadata.get("document_id"),
                            "chunk_index": doc.metadata.get("chunk_index"),
                            "metadata": doc.metadata,
                        }
                    )
            
            # Create citations
            citations = [
                Citation(
                    document_id=r["document_id"],
                    chunk_index=r.get("chunk_index", 0),
                    content=r["content"],
                    score=r["score"],
                    metadata=r.get("metadata", {}),
                )
                for r in results
            ]
            rag_query.citations = citations
            
            # Format response with citations
            # Normalize results for compatibility: ensure 'document_id' and 'source' are top-level
            for r in results:
                meta = r.get("metadata") or {}
                if not r.get("document_id") and meta.get("document_id"):
                    r["document_id"] = meta.get("document_id")
                if not r.get("source") and meta.get("source"):
                    r["source"] = meta.get("source")

            return {
                "results": [
                    {
                        "content": r["content"],
                        "score": r["score"],
                        "document_id": r["document_id"],
                        "chunk_index": r.get("chunk_index"),
                        "metadata": r.get("metadata", {}),
                    }
                    for r in results
                ],
                "citations": [
                    {
                        "document_id": c.document_id,
                        "chunk_index": c.chunk_index,
                        "content": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                        "score": c.score,
                        "metadata": c.metadata,
                    }
                    for c in citations
                ],
                "query_metadata": {
                    "original_query": query,
                    "rewritten_queries": rag_query.rewritten_queries,
                    "num_results": len(results),
                },
            }

        except Exception as e:
            logger.error(f"Search failed for project {project_id}: {e}")
            return {
                "results": [],
                "citations": [],
                "query_metadata": {"original_query": query, "error": str(e)},
            }

    def refine_query(
        self,
        project_id: str,
        original_query: str,
        previous_results: List[Dict],
    ) -> str:
        """
        Refine a query based on previous search results.
        """
        if not previous_results:
            return original_query
        
        # Previous results may come from document chunks (with 'content')
        # or from knowledge nodes (with 'summary' or 'title'). Be permissive.
        def _extract_content(r: Dict) -> str:
            if 'content' in r and r['content']:
                return r['content']
            if r.get('summary'):
                return r['summary']
            if r.get('title'):
                return r['title']
            if r.get('metadata') and isinstance(r.get('metadata'), dict):
                return r['metadata'].get('content') or r['metadata'].get('summary') or ''
            return str(r)

        context = "\n".join([
            f"- {_extract_content(r)[:150]}..." for r in previous_results[:3]
        ])
        
        prompt = f"""The user searched for: "{original_query}"

These results were found:
{context}

The user wants to refine their search. Generate a more specific query that would help find better results.
Return only the refined query, no explanation.
"""
        
        try:
            refined = generate_text(
                prompt=prompt,
                project_id=project_id,
                temperature=0.2,
            ).response.strip()
            return refined
        except Exception as e:
            logger.warning(f"Query refinement failed: {e}")
            return original_query

    def get_query_history(self, project_id: str, limit: int = 10) -> List[RAGQuery]:
        """Get query history for a project."""
        history = self._query_history.get(project_id, [])
        return history[-limit:] if history else []

    def record_query(self, project_id: str, query: str) -> None:
        """Record a query in the RAG query history for the project.

        This can be called by other services (e.g., knowledge_service) to capture
        queries invoked via compatibility endpoints.
        """
        rag_query = RAGQuery(query=query, project_id=project_id, timestamp=datetime.now())
        if project_id not in self._query_history:
            self._query_history[project_id] = []
        self._query_history[project_id].append(rag_query)

    def delete_document(
        self,
        project_id: str,
        document_id: str,
    ) -> bool:
        """
        Delete all chunks for a document from Qdrant.
        """
        try:
            collection_name = self.qdrant_service._get_collection_name(project_id, "documents")
            if not self.qdrant_service.client or not self.qdrant_service.client.collection_exists(collection_name):
                return False

            # Use filter to delete all chunks for this document
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filter_condition = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
            self.qdrant_service.client.delete(
                collection_name=collection_name,
                points_selector=filter_condition,
            )

            logger.info(f"Deleted document {document_id} from project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False


rag_service = RagService()
