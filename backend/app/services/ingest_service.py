from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import IngestJob, IngestRequest, IngestStatus
from app.services.rag_service import rag_service
from app.services.streaming_service import emit_ingest_event
from app.services.chat_parser_service import chat_parser_service
from app.services.idea_service import idea_service
from app.services.repo_service import repo_service

logger = logging.getLogger(__name__)


class IngestService:
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

    from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import IngestJob, IngestRequest, IngestStatus
from app.services.rag_service import rag_service
from app.services.streaming_service import emit_ingest_event
from app.services.chat_parser_service import chat_parser_service
from app.services.idea_service import idea_service
from app.services.repo_service import repo_service

logger = logging.getLogger(__name__)


class IngestService:
    # ... (list_jobs, get_job, create_job, cancel_job, delete_job methods remain the same)
    
    async def process_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return

        loop = asyncio.get_running_loop()

        await self.update_job(job_id, status=IngestStatus.RUNNING, progress=0.1, message="Processing...")

        try:
            file_path = job.source_path
            
            # This is a blocking I/O check, run in executor
            file_exists = await loop.run_in_executor(None, Path(file_path).exists)

            if not file_exists:
                await self.update_job(job_id, status=IngestStatus.FAILED, message=f"File not found: {file_path}")
                return

            text = ""
            is_chat_export = self._is_chat_export(file_path)
            is_repo = self._is_repository(file_path)

            if is_repo:
                try:
                    stats = await loop.run_in_executor(
                        None, 
                        repo_service.index_repository,
                        job.project_id,
                        file_path
                    )
                    await self.update_job(job_id, progress=0.7, message=f"Indexed {stats['files_indexed']} files.")
                    text = await loop.run_in_executor(None, self._extract_repo_documentation, file_path)
                except Exception as e:
                    logger.error(f"Repo indexing failed: {e}")
                    await self.update_job(job_id, progress=0.5, message=f"Repo indexing error: {str(e)}")

            elif is_chat_export:
                # Assuming chat parsing is also potentially blocking
                try:
                    parsed_data = await loop.run_in_executor(
                        None,
                        chat_parser_service.parse_chat_export,
                        file_path,
                        job.project_id
                    )
                    # ... (idea creation logic remains, could also be made async if it has I/O)
                    text = "\n\n".join([msg.get("content", "") for msg in parsed_data.get("conversations", [])])
                    await self.update_job(job_id, progress=0.5, message=f"Parsed chat export.")
                except Exception as e:
                    logger.error(f"Chat parsing failed: {e}")
                    is_chat_export = False
            
            if not text: # If not a repo or chat, or if they failed and produced no text
                text = await self._read_file_content(file_path)

            if text is None:
                await self.update_job(job_id, status=IngestStatus.FAILED, message=f"Could not read file: {file_path}")
                return

            metadata = {"source": job.source_path, "job_id": job_id}
            
            # rag_service might be CPU bound for chunking
            chunks_created = await loop.run_in_executor(
                None,
                rag_service.ingest_document,
                job.project_id,
                f"ingest_{job_id}",
                text,
                metadata
            )
            
            if chunks_created > 0:
                await self.update_job(job_id, progress=0.8, message=f"Indexed {chunks_created} chunks.")

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

    async def _read_file_content(self, file_path: str) -> Optional[str]:
        loop = asyncio.get_running_loop()
        try:
            if file_path.lower().endswith(".pdf"):
                import pypdf
                
                def read_pdf():
                    text = ""
                    with open(file_path, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        for page in reader.pages:
                            text += page.extract_text()
                    return text
                
                return await loop.run_in_executor(None, read_pdf)
            else:
                def read_text():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            return f.read()
                    except: # Fallback for other encodings
                        with open(file_path, "r", encoding="latin-1") as f:
                            return f.read()
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
        # This method interacts with the DB, so it should also be async
        # For simplicity in this refactor, we'll make it async but keep the blocking DB call.
        # In a real scenario, you'd use an async DB driver (e.g., asyncpg, databases).
        
        def db_update():
            with db_session() as conn:
                updates = []
                params = []

                if status:
                    updates.append("status = ?")
                    params.append(status.value)
                # ... (rest of the update logic)
                
                updates.append("updated_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
                params.append(job_id)

                query = f"UPDATE ingest_jobs SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()
            return self.get_job(job_id)

        updated_job = await asyncio.get_running_loop().run_in_executor(None, db_update)

        if updated_job and status:
            await emit_ingest_event(updated_job.project_id, f"ingest.job.{status.value}", updated_job.model_dump())
        
        return updated_job

    # ... (other methods like _row_to_job, _is_chat_export, etc. remain the same)


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

    def _is_chat_export(self, file_path: str) -> bool:
        """Check if file is a chat export based on filename patterns."""
        filename_lower = file_path.lower()
        chat_patterns = [
            "chat", "conversation", "export", "history", "messages",
            "claude", "chatgpt", "gpt", "bard", "gemini",
        ]
        return any(pattern in filename_lower for pattern in chat_patterns)

    def _is_repository(self, file_path: str) -> bool:
        """Check if path is a git repository."""
        path_obj = Path(file_path)
        return path_obj.is_dir() and (path_obj / ".git").exists()

    def _should_use_deep_ingest(self, file_path: str) -> bool:
        """
        Determine if file requires deep ingest (SUPER_READER lane).
        
        Deep ingest is used for:
        - Large files (>50MB)
        - Git repositories (monorepo analysis)
        - Files that require extensive context analysis
        """
        import os
        if not os.path.exists(file_path):
            return False
        
        # Check file size (>50MB suggests large content)
        if os.path.isfile(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 50:
                logger.info(f"File {file_path} is {file_size_mb:.1f}MB, using deep ingest")
                return True
        
        # Check if it's a repository (always use deep ingest for repos)
        if self._is_repository(file_path):
            logger.info(f"Repository detected at {file_path}, using deep ingest")
            return True
        
        return False

    def _extract_repo_documentation(self, repo_path: str) -> str:
        """Extract documentation files from repository for RAG."""
        repo_path_obj = Path(repo_path)
        doc_files = []
        doc_patterns = ["README.md", "README.txt", "docs/", "*.md"]

        # Look for README files
        for pattern in ["README.md", "README.txt", "README.rst"]:
            readme_path = repo_path_obj / pattern
            if readme_path.exists():
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        doc_files.append(f.read())
                except Exception:
                    pass

        # Look for docs directory
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