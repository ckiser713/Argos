from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import IngestJob, IngestRequest, IngestStatus
from app.services.rag_service import rag_service
from app.services.streaming_service import emit_ingest_event
from app.services.idea_service import idea_service
from app.services.repo_service import repo_service

from langchain_classic.chains import create_extraction_chain_pydantic
from app.services.local_llm_client import LocalChatLLM
from app.config import get_settings


logger = logging.getLogger(__name__)

# --- Pydantic Models for AI-driven Extraction ---

class DocumentType(str, Enum):
    CHAT_EXPORT = "chat_export"
    TECHNICAL_DOCS = "technical_docs"
    SOURCE_CODE = "source_code"
    OTHER = "other"

class DocumentMetadata(BaseModel):
    document_type: DocumentType = Field(
        ...,
        description="The type of the document, e.g., chat transcript, source code, or technical documentation.",
    )
    summary: str = Field(
        ...,
        description="A concise, one-sentence summary of the document's content.",
    )
    detected_topics: List[str] = Field(
        default_factory=list,
        description="A list of key topics or technologies mentioned in the document.",
    )

class ChatMessage(BaseModel):
    sender: str
    timestamp: str
    content: str

class ChatExport(BaseModel):
    messages: List[ChatMessage]

# --- End Pydantic Models ---


class IngestService:
    def __init__(self):
        # Initialize the LLM lazily. If local LLM is not available,
        # keep the LLM and extraction chains as None and skip LLM-based features.
        self.llm = None
        self.metadata_extraction_chain = None
        self.chat_extraction_chain = None
        try:
            settings = get_settings()
            self.llm = LocalChatLLM(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model_name=settings.llm_model_name,
                temperature=0
            )
            # Create the extraction chains only if an LLM is available
            self.metadata_extraction_chain = create_extraction_chain_pydantic(
                pydantic_schema=DocumentMetadata, llm=self.llm
            )
            self.chat_extraction_chain = create_extraction_chain_pydantic(
                pydantic_schema=ChatExport, llm=self.llm
            )
        except Exception as e:
            logger.warning("Local LLM client not configured: %s. Skipping LLM initialization.", e)

    async def _get_document_metadata(self, content: str) -> Optional[DocumentMetadata]:
        """Uses an LLM chain to extract metadata from document content."""
        loop = asyncio.get_running_loop()
        # If LLM/extraction chain isn't available (e.g., local/test env), skip.
        if not self.metadata_extraction_chain:
            logger.debug("Skipping metadata extraction; LLM/extraction chain not configured.")
            return None
        try:
            # LangChain's predict is synchronous, so run it in an executor
            extracted_data = await loop.run_in_executor(
                None, self.metadata_extraction_chain.invoke, {"input": content}
            )
            if extracted_data and extracted_data.get("text"):
                return extracted_data["text"][0]
        except Exception as e:
            logger.error(f"Failed to extract document metadata: {e}")
        return None

    async def _parse_chat_export_with_ai(self, content: str) -> Optional[ChatExport]:
        """Uses a specialized LLM chain to parse a chat export into structured messages."""
        loop = asyncio.get_running_loop()
        # If LLM/extraction chain isn't available (e.g., local/test env), skip.
        if not self.chat_extraction_chain:
            logger.debug("Skipping chat parsing; LLM/extraction chain not configured.")
            return None
        try:
            extracted_data = await loop.run_in_executor(
                None, self.chat_extraction_chain.invoke, {"input": content}
            )
            if extracted_data and extracted_data.get("text"):
                return extracted_data["text"][0]
        except Exception as e:
            logger.error(f"Failed to parse chat export with AI: {e}")
        return None


    def list_jobs(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM ingest_jobs WHERE project_id = ? AND deleted_at IS NULL"
            params = [project_id]

            if status:
                query += " AND status = ?"
                params.append(status)
            if stage:
                query += " AND stage = ?"
                params.append(stage)
            if source_id:
                query += " AND source_id = ?"
                params.append(source_id)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit + 1)

            rows = conn.execute(query, params).fetchall()

            items = []
            for row in rows[:limit]:
                items.append(self._row_to_job(row))

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            # Get total count
            count_query = "SELECT COUNT(*) as total FROM ingest_jobs WHERE project_id = ? AND deleted_at IS NULL"
            count_params = [project_id]
            if status:
                count_query += " AND status = ?"
                count_params.append(status)
            if stage:
                count_query += " AND stage = ?"
                count_params.append(stage)
            if source_id:
                count_query += " AND source_id = ?"
                count_params.append(source_id)

            total_row = conn.execute(count_query, count_params).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def get_job(self, job_id: str) -> Optional[IngestJob]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM ingest_jobs WHERE id = ? AND deleted_at IS NULL", (job_id,)).fetchone()
            if row:
                return self._row_to_job(row)
        return None

    def create_job(self, project_id: str, request: IngestRequest) -> IngestJob:
        now = datetime.now(timezone.utc)
        job_id = str(uuid.uuid4())

        # Create a default source if needed
        source_id = "default_source"
        with db_session() as conn:
            # Check if source exists, create if not
            source_row = conn.execute(
                "SELECT id FROM ingest_sources WHERE project_id = ? LIMIT 1", (project_id,)
            ).fetchone()
            if not source_row:
                source_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO ingest_sources
                    (id, project_id, kind, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (source_id, project_id, "file", "Default Source", now.isoformat(), now.isoformat()),
                )
            else:
                source_id = source_row["id"]

        original_filename = request.source_path.split("/")[-1]
        job = IngestJob(
            id=job_id,
            project_id=project_id,
            source_path=request.source_path,
            original_filename=original_filename,
            created_at=now,
            updated_at=now,
            status=IngestStatus.QUEUED,
            progress=0.0,
            message="Job queued.",
            stage="initial",
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO ingest_jobs
                (id, project_id, source_id, source_path, original_filename, status, created_at, updated_at, stage, progress, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    project_id,
                    source_id,
                    request.source_path,
                    original_filename,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.stage,
                    job.progress,
                    job.message,
                ),
            )
            conn.commit()
        
        # Emit job created event
        try:
            pass  # asyncio.create_task(emit_ingest_event(project_id, "ingest.job.created", job.model_dump()))
        except RuntimeError:
            pass  # Ignore event emission errors if no event loop is running
        
        return job

    def cancel_job(self, job_id: str) -> IngestJob:
        now = datetime.now(timezone.utc)
        with db_session() as conn:
            conn.execute(
                """
                UPDATE ingest_jobs
                SET status = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (IngestStatus.CANCELLED.value, now.isoformat(), now.isoformat(), job_id),
            )
            conn.commit()
        
        job = self.get_job(job_id)
        
        # Emit job cancelled event
        if job:
            try:
                pass  # asyncio.create_task(emit_ingest_event(job.project_id, "ingest.job.cancelled", job.model_dump()))
            except RuntimeError:
                pass  # Ignore event emission errors if no event loop is running
        
        return job

    def delete_job(self, job_id: str) -> None:
        now = datetime.now(timezone.utc)
        with db_session() as conn:
            conn.execute(
                """
                UPDATE ingest_jobs
                SET deleted_at = ?, status = ?
                WHERE id = ?
                """,
                (now.isoformat(), IngestStatus.CANCELLED.value, job_id),
            )
            conn.commit()

    # duplicate imports removed; methods continue
    
    async def process_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return

        loop = asyncio.get_running_loop()
        await self.update_job(job_id, status=IngestStatus.RUNNING, progress=0.1, message="Analyzing file type...")

        try:
            file_path = job.source_path
            file_exists = await loop.run_in_executor(None, Path(file_path).exists)

            if not file_exists:
                await self.update_job(job_id, status=IngestStatus.FAILED, message=f"File not found: {file_path}")
                return

            text_to_process = ""
            is_repo = self._is_repository(file_path)

            if is_repo:
                # Handle repositories separately as they are directories
                await self.update_job(job_id, progress=0.2, message="Indexing repository...")
                try:
                    stats = await loop.run_in_executor(None, repo_service.index_repository, job.project_id, file_path)
                    await self.update_job(job_id, progress=0.7, message=f"Indexed {stats['files_indexed']} files.")
                    text_to_process = await loop.run_in_executor(None, self._extract_repo_documentation, file_path)
                except Exception as e:
                    logger.error(f"Repo indexing failed: {e}")
                    await self.update_job(job_id, progress=0.5, message=f"Repo indexing error: {str(e)}")

            else:
                # For files, use AI to determine type and extract content
                content_preview = await self._read_file_content(file_path, limit=2000)
                if content_preview is None:
                    await self.update_job(job_id, status=IngestStatus.FAILED, message=f"Could not read file: {file_path}")
                    return

                doc_metadata = await self._get_document_metadata(content_preview)

                if doc_metadata and doc_metadata.document_type == DocumentType.CHAT_EXPORT:
                    await self.update_job(job_id, progress=0.3, message="Parsing chat export...")
                    full_content = await self._read_file_content(file_path)
                    if not full_content:
                        await self.update_job(job_id, status=IngestStatus.FAILED, message="Failed to read full chat export.")
                        return

                    parsed_chat = await self._parse_chat_export_with_ai(full_content)
                    if parsed_chat:
                        text_to_process = "\n\n".join([f"{msg.sender} ({msg.timestamp}): {msg.content}" for msg in parsed_chat.messages])
                        await self.update_job(job_id, progress=0.5, message=f"Successfully parsed chat with {len(parsed_chat.messages)} messages.")
                    else:
                        await self.update_job(job_id, progress=0.4, message="AI parsing failed, falling back to basic text extraction.")
                        text_to_process = full_content
                else:
                    doc_type_msg = f"Detected document type: {doc_metadata.document_type.value if doc_metadata else 'other'}."
                    await self.update_job(job_id, progress=0.3, message=doc_type_msg)
                    text_to_process = await self._read_file_content(file_path)

            if not text_to_process:
                await self.update_job(job_id, status=IngestStatus.FAILED, message="No text could be extracted from the source.")
                return

            await self.update_job(job_id, progress=0.7, message="Indexing document content...")
            metadata = {"source": job.source_path, "job_id": job_id}
            
            chunks_created = await loop.run_in_executor(
                None,
                rag_service.ingest_document,
                job.project_id,
                f"ingest_{job_id}",
                text_to_process,
                metadata
            )
            
            if chunks_created > 0:
                await self.update_job(job_id, progress=0.9, message=f"Indexed {chunks_created} chunks.")

            await self.update_job(
                job_id,
                status=IngestStatus.COMPLETED,
                progress=1.0,
                message="Ingested successfully.",
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.exception(f"Error processing job {job_id}")
            await self.update_job(job_id, status=IngestStatus.FAILED, message=str(e), error_message=str(e))

    async def _read_file_content(self, file_path: str, limit: Optional[int] = None) -> Optional[str]:
        loop = asyncio.get_running_loop()
        try:
            if file_path.lower().endswith(".pdf"):
                import pypdf
                
                def read_pdf():
                    text = ""
                    with open(file_path, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        for page in reader.pages:
                            text += page.extract_text() or ""
                            if limit and len(text) >= limit:
                                return text[:limit]
                    return text
                
                return await loop.run_in_executor(None, read_pdf)
            else:
                def read_text():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            return f.read(limit)
                    except UnicodeDecodeError:
                        with open(file_path, "r", encoding="latin-1") as f:
                            return f.read(limit)
                return await loop.run_in_executor(None, read_text)
        except Exception as e:
            logger.error(f"Failed to read file content for {file_path}: {e}")
            return None
    
    async def update_job(
        self,
        job_id: str,
        *,
        status: Optional[IngestStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[IngestJob]:
        def db_update():
            with db_session() as conn:
                updates = []
                params = []

                if status:
                    updates.append("status = ?")
                    params.append(status.value)
                if progress is not None:
                    updates.append("progress = ?")
                    params.append(progress)
                if message:
                    updates.append("message = ?")
                    params.append(message)
                if error_message:
                    updates.append("error_message = ?")
                    params.append(error_message)
                if completed_at:
                    updates.append("completed_at = ?")
                    params.append(completed_at.isoformat())
                
                if not updates:
                    return self.get_job(job_id)

                updates.append("updated_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
                params.append(job_id)

                query = f"UPDATE ingest_jobs SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()
            return self.get_job(job_id)

        updated_job = await asyncio.get_running_loop().run_in_executor(None, db_update)

        if updated_job:
             asyncio.create_task(emit_ingest_event(updated_job.project_id, "ingest.job.updated", updated_job.model_dump()))
        
        return updated_job

    def _row_to_job(self, row) -> IngestJob:
        return IngestJob(
            id=row["id"],
            project_id=row["project_id"],
            source_path=row.get("source_path") or row["original_filename"] or "",
            original_filename=row["original_filename"],
            byte_size=row["byte_size"] if "byte_size" in row.keys() else None,
            mime_type=row["mime_type"] if "mime_type" in row.keys() else None,
            stage=row["stage"] if "stage" in row.keys() else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if "updated_at" in row.keys() and row["updated_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if "completed_at" in row.keys() and row["completed_at"] else None,
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if "deleted_at" in row.keys() and row["deleted_at"] else None,
            status=IngestStatus(row["status"]),
            progress=row["progress"] if "progress" in row.keys() else 0.0,
            message=row["message"] if "message" in row.keys() else None,
            error_message=row["error_message"] if "error_message" in row.keys() else None,
            canonical_document_id=row["canonical_document_id"] if "canonical_document_id" in row.keys() else None,
        )

    def _is_repository(self, file_path: str) -> bool:
        """Check if path is a git repository."""
        path_obj = Path(file_path)
        return path_obj.is_dir() and (path_obj / ".git").exists()

    def _extract_repo_documentation(self, repo_path: str) -> str:
        """Extract documentation files from repository for RAG."""
        repo_path_obj = Path(repo_path)
        doc_files = []
        doc_patterns = ["README.md", "README.txt", "docs/", "*.md"]

        for pattern in ["README.md", "README.txt", "README.rst"]:
            readme_path = repo_path_obj / pattern
            if readme_path.exists():
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        doc_files.append(f.read())
                except Exception:
                    pass

        docs_dir = repo_path_obj / "docs"
        if docs_dir.exists():
            for doc_file in docs_dir.rglob("*.md"):
                try:
                    with open(doc_file, "r", encoding="utf-8") as f:
                        doc_files.append(f.read())
                except Exception:
                    pass

        return "\n\n".join(doc_files)


ingest_service = IngestService()