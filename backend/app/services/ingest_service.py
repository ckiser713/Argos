from __future__ import annotations

import asyncio
import asyncio
import hashlib
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from enum import Enum
from pydantic import BaseModel, Field

from app.database import get_db_session
from app.domain.common import PaginatedResponse
from app.domain.models import IngestJob as IngestJobDTO, IngestRequest, IngestStatus
from app.models import IngestJob as ORMIngestJob, IngestSource
from app.observability import record_ingest_transition, set_ingest_gauge
from app.services.rag_service import rag_service
from app.services.streaming_service import emit_ingest_event
from app.services.repo_service import repo_service
from app.services.storage_service import storage_service

from langchain_classic.chains import create_extraction_chain_pydantic
from app.services.local_llm_client import LocalChatLLM
from app.config import get_settings
from sqlalchemy import func


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
        self.settings = get_settings()
        self.llm = None
        self.metadata_extraction_chain = None
        self.chat_extraction_chain = None
        try:
            self.llm = LocalChatLLM(
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                model_name=self.settings.llm_model_name,
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
        with get_db_session() as session:
            query = (
                session.query(ORMIngestJob)
                .filter(ORMIngestJob.project_id == project_id)
                .filter(ORMIngestJob.deleted_at.is_(None))
            )
            if status:
                query = query.filter(ORMIngestJob.status == status)
            if stage:
                query = query.filter(ORMIngestJob.stage == stage)
            if source_id:
                query = query.filter(ORMIngestJob.source_id == source_id)

            rows = query.order_by(ORMIngestJob.created_at.desc()).limit(limit + 1).all()
            items = [self._row_to_job(row) for row in rows[:limit]]
            next_cursor = rows[limit].id if len(rows) > limit else None
            total = query.order_by(None).count()
            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def get_job(self, job_id: str) -> Optional[IngestJobDTO]:
        with get_db_session() as session:
            job = session.get(ORMIngestJob, job_id)
            if job and not job.deleted_at:
                return self._row_to_job(job)
        return None

    def _get_or_create_source(self, session, project_id: str) -> str:
        existing = session.query(IngestSource).filter(IngestSource.project_id == project_id).first()
        if existing:
            return existing.id
        now_iso = datetime.now(timezone.utc).isoformat()
        source = IngestSource(
            id=str(uuid.uuid4()),
            project_id=project_id,
            kind="file",
            name="Default Source",
            created_at=now_iso,
            updated_at=now_iso,
        )
        session.add(source)
        session.flush()
        return source.id

    def create_job(self, project_id: str, request: IngestRequest) -> IngestJobDTO:
        now = datetime.now(timezone.utc).isoformat()
        source_uri = request.source_uri or request.source_path
        if not source_uri:
            raise ValueError("source_uri is required to create an ingest job")
        parsed = urlparse(source_uri)
        guessed_name = Path(parsed.path or request.source_path or "").name or Path(str(source_uri)).name
        original_filename = request.original_filename or guessed_name or "upload"

        with get_db_session() as session:
            source_id = self._get_or_create_source(session, project_id)
            job = ORMIngestJob(
                id=str(uuid.uuid4()),
                project_id=project_id,
                source_id=source_id,
                source_path=request.source_path or source_uri,
                source_uri=source_uri,
                original_filename=original_filename,
                byte_size=request.byte_size or 0,
                mime_type=request.mime_type,
                checksum=request.checksum,
                stage="initial",
                progress=0.0,
                status=IngestStatus.QUEUED.value,
                created_at=now,
                updated_at=now,
                message="Job queued.",
            )
            session.add(job)
            session.commit()
            session.refresh(job)

        created_job = self._row_to_job(job)
        try:
            pass  # asyncio.create_task(emit_ingest_event(project_id, "ingest.job.created", created_job.model_dump()))
        except RuntimeError:
            pass
        return created_job

    def enqueue_job(self, job_id: str) -> str:
        if self.settings.tasks_eager:
            return self._run_inline_with_retries(job_id)
        from app.tasks.ingest_tasks import process_ingest_job_task

        result = process_ingest_job_task.apply_async(args=[job_id], queue="ingest")
        task_id = result.id
        with get_db_session() as session:
            job = session.get(ORMIngestJob, job_id)
            if job:
                job.task_id = task_id
                job.updated_at = datetime.now(timezone.utc).isoformat()
                session.commit()
        return task_id

    def _run_inline_with_retries(self, job_id: str) -> str:
        attempts = 0
        max_attempts = max(1, self.settings.task_max_retries)
        last_exc: Optional[Exception] = None
        inline_task_id = f"inline-{job_id}"
        asyncio.run(self.update_job(job_id, task_id=inline_task_id))
        while attempts < max_attempts:
            try:
                asyncio.run(self.process_job(job_id, mark_failed=False))
                return f"inline-{job_id}"
            except Exception as exc:  # noqa: BLE001
                attempts += 1
                last_exc = exc
                if attempts >= max_attempts:
                    asyncio.run(
                        self.update_job(
                            job_id,
                            status=IngestStatus.FAILED,
                            message="Ingest failed after retries",
                            error_message=str(exc),
                            completed_at=datetime.now(timezone.utc),
                        )
                    )
                    break
                asyncio.run(
                    self.update_job(
                        job_id,
                        status=IngestStatus.RUNNING,
                        message=f"Retrying ingest (attempt {attempts + 1}/{max_attempts})",
                        error_message=str(exc),
                    )
                )
        if last_exc:
            raise last_exc
        return f"inline-{job_id}"

    def cancel_job(self, job_id: str) -> Optional[IngestJobDTO]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db_session() as session:
            job = session.get(ORMIngestJob, job_id)
            if not job:
                return None
            job.status = IngestStatus.CANCELLED.value
            job.updated_at = now
            job.completed_at = now
            session.commit()
            session.refresh(job)
            cancelled = self._row_to_job(job)
        try:
            pass  # asyncio.create_task(emit_ingest_event(job.project_id, "ingest.job.cancelled", cancelled.model_dump()))
        except RuntimeError:
            pass
        return cancelled

    def delete_job(self, job_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_db_session() as session:
            job = session.get(ORMIngestJob, job_id)
            if not job:
                return
            job.deleted_at = now
            job.status = IngestStatus.CANCELLED.value
            job.updated_at = now
            session.commit()

    # duplicate imports removed; methods continue
    
    async def process_job(self, job_id: str, *, mark_failed: bool = True):
        job = self.get_job(job_id)
        if not job:
            return

        loop = asyncio.get_running_loop()
        started_at = datetime.now(timezone.utc)
        await self.update_job(
            job_id,
            status=IngestStatus.RUNNING,
            progress=0.1,
            message="Analyzing source...",
            started_at=started_at,
        )

        temp_dir: Optional[Path] = None
        try:
            source_uri = job.source_uri or job.source_path
            if not source_uri:
                raise FileNotFoundError("No source_uri or source_path available for ingest job")

            parsed = urlparse(source_uri)
            if parsed.scheme == "s3":
                local_path = await loop.run_in_executor(None, storage_service.download_to_path, source_uri)
                temp_dir = local_path.parent
            elif parsed.scheme == "file":
                local_path = Path(parsed.path)
            else:
                local_path = Path(source_uri)

            file_exists = await loop.run_in_executor(None, local_path.exists)
            if not file_exists:
                raise FileNotFoundError(f"File not found: {local_path}")

            if local_path.is_file() and job.checksum:
                actual_checksum = await loop.run_in_executor(None, self._checksum_file, local_path)
                if actual_checksum != job.checksum:
                    raise ValueError("Checksum mismatch for stored ingest object")

            text_to_process = ""
            is_repo = self._is_repository(str(local_path))

            if is_repo:
                await self.update_job(job_id, progress=0.2, message="Indexing repository...")
                try:
                    stats = await loop.run_in_executor(
                        None, repo_service.index_repository, job.project_id, str(local_path)
                    )
                    await self.update_job(job_id, progress=0.7, message=f"Indexed {stats['files_indexed']} files.")
                    text_to_process = await loop.run_in_executor(
                        None, self._extract_repo_documentation, str(local_path)
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Repo indexing failed: {e}")
                    await self.update_job(job_id, progress=0.5, message=f"Repo indexing error: {str(e)}")

            else:
                content_preview = await self._read_file_content(str(local_path), limit=2000)
                if content_preview is None:
                    raise FileNotFoundError(f"Could not read file: {local_path}")

                doc_metadata = await self._get_document_metadata(content_preview)

                if doc_metadata and doc_metadata.document_type == DocumentType.CHAT_EXPORT:
                    await self.update_job(job_id, progress=0.3, message="Parsing chat export...")
                    full_content = await self._read_file_content(str(local_path))
                    if not full_content:
                        raise ValueError("Failed to read full chat export.")

                    parsed_chat = await self._parse_chat_export_with_ai(full_content)
                    if parsed_chat:
                        text_to_process = "\n\n".join(
                            [f"{msg.sender} ({msg.timestamp}): {msg.content}" for msg in parsed_chat.messages]
                        )
                        await self.update_job(
                            job_id,
                            progress=0.5,
                            message=f"Successfully parsed chat with {len(parsed_chat.messages)} messages.",
                        )
                    else:
                        await self.update_job(
                            job_id, progress=0.4, message="AI parsing failed, falling back to basic text extraction."
                        )
                        text_to_process = full_content
                else:
                    doc_type_msg = f"Detected document type: {doc_metadata.document_type.value if doc_metadata else 'other'}."
                    await self.update_job(job_id, progress=0.3, message=doc_type_msg)
                    text_to_process = await self._read_file_content(str(local_path))

            if not text_to_process:
                raise ValueError("No text could be extracted from the source.")

            await self.update_job(job_id, progress=0.7, message="Indexing document content...")
            metadata = {"source": job.source_uri or job.source_path, "job_id": job_id, "filename": job.original_filename}

            chunks_created = await loop.run_in_executor(
                None,
                rag_service.ingest_document,
                job.project_id,
                f"ingest_{job_id}",
                text_to_process,
                metadata,
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

        except Exception as e:  # noqa: BLE001
            logger.exception("Error processing job %s", job_id)
            if mark_failed:
                await self.update_job(
                    job_id,
                    status=IngestStatus.FAILED,
                    message=str(e),
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
            raise
        finally:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

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
        started_at: Optional[datetime] = None,
        task_id: Optional[str] = None,
    ) -> Optional[IngestJobDTO]:
        def db_update():
            with get_db_session() as session:
                job = session.get(ORMIngestJob, job_id)
                if not job:
                    return None

                previous_status = job.status

                if status:
                    job.status = status.value
                if progress is not None:
                    job.progress = progress
                if message is not None:
                    job.message = message
                if error_message is not None:
                    job.error_message = error_message
                if completed_at:
                    job.completed_at = completed_at.isoformat()
                if started_at:
                    job.started_at = started_at.isoformat()
                if task_id:
                    job.task_id = task_id

                job.updated_at = datetime.now(timezone.utc).isoformat()
                session.commit()
                session.refresh(job)

                if status and previous_status != job.status:
                    try:
                        record_ingest_transition(str(job.status))
                    except Exception:  # pragma: no cover - metrics best-effort
                        logger.debug("Failed to record ingest metrics", exc_info=True)
                    try:
                        counts = dict(
                            session.query(ORMIngestJob.status, func.count(ORMIngestJob.id))
                            .group_by(ORMIngestJob.status)
                            .all()
                        )
                        set_ingest_gauge({str(k): int(v) for k, v in counts.items()})
                    except Exception:  # pragma: no cover - metrics best-effort
                        logger.debug("Failed to refresh ingest gauges", exc_info=True)
                return self._row_to_job(job)

        updated_job = await asyncio.get_running_loop().run_in_executor(None, db_update)

        if updated_job:
            try:
                asyncio.create_task(
                    emit_ingest_event(
                        updated_job.project_id, "ingest.job.updated", updated_job.model_dump()
                    )
                )
            except RuntimeError:
                pass

        return updated_job

    def _row_to_job(self, row) -> IngestJobDTO:
        def _get(key: str):
            if isinstance(row, dict):
                return row.get(key)
            return getattr(row, key, None)

        return IngestJobDTO(
            id=_get("id"),
            project_id=_get("project_id"),
            source_path=_get("source_path") or _get("original_filename") or "",
            source_uri=_get("source_uri") or _get("source_path"),
            original_filename=_get("original_filename"),
            byte_size=_get("byte_size"),
            mime_type=_get("mime_type"),
            checksum=_get("checksum"),
            stage=_get("stage"),
            created_at=datetime.fromisoformat(_get("created_at")) if _get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(_get("updated_at")) if _get("updated_at") else None,
            started_at=datetime.fromisoformat(_get("started_at")) if _get("started_at") else None,
            completed_at=datetime.fromisoformat(_get("completed_at")) if _get("completed_at") else None,
            deleted_at=datetime.fromisoformat(_get("deleted_at")) if _get("deleted_at") else None,
            status=IngestStatus(_get("status")),
            progress=_get("progress") or 0.0,
            message=_get("message"),
            error_message=_get("error_message"),
            canonical_document_id=_get("canonical_document_id"),
            task_id=_get("task_id"),
        )

    def _checksum_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

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
