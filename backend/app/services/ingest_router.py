from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

# Placeholder for actual services
class StrategyService(Protocol):
    def process(self, path: Path) -> None:
        ...

class KnowledgeService(Protocol):
    def process(self, path: Path, lane: str) -> None:
        ...

class RepoService(Protocol):
    def process(self, path: Path, lane: str) -> None:
        ...

class IngestRouter:
    def __init__(
        self,
        strategy_service: StrategyService,
        knowledge_service: KnowledgeService,
        repo_service: RepoService,
    ):
        self.strategy_service = strategy_service
        self.knowledge_service = knowledge_service
        self.repo_service = repo_service

    def route(self, file_path: str) -> None:
        """
        Inspects the incoming file path and routes it to the appropriate service.
        """
        path = Path(file_path)
        path_str = str(path)

        # Handle NotebookLM exports
        if self._is_notebooklm_export(path):
            # Custom logic to preserve NotebookLM clusters
            print(f"Routing NotebookLM export: {path_str} to KnowledgeService (special handling)")
            self.knowledge_service.process(path, lane="Super-Reader") # Or a dedicated lane
            return

        if "/chat_services/" in path_str:
            print(f"Routing chat log: {path_str} to StrategyService")
            self.strategy_service.process(path)
        elif "/docs/" in path_str:
            print(f"Routing document: {path_str} to KnowledgeService (Super-Reader Lane)")
            self.knowledge_service.process(path, lane="Super-Reader")
        elif "/repos/" in path_str:
            print(f"Routing repository code: {path_str} to RepoService (Coder Lane)")
            self.repo_service.process(path, lane="Coder")
        else:
            print(f"No route found for path: {path_str}")

    def _is_notebooklm_export(self, path: Path) -> bool:
        """
        Detects if a path is a NotebookLM export by checking for a specific
        folder structure. A NotebookLM export is a directory containing .txt files
        and a 'source_documents' subdirectory.
        """
        if path.is_dir():
            has_txt_files = any(f.suffix == '.txt' for f in path.iterdir() if f.is_file())
            has_source_docs = (path / 'source_documents').is_dir()
            if has_txt_files and has_source_docs:
                return True
        return False

# Example Usage (for demonstration purposes):
if __name__ == "__main__":

    class MockStrategyService:
        def process(self, path: Path) -> None:
            print(f"StrategyService processing {path}")

    class MockKnowledgeService:
        def process(self, path: Path, lane: str) -> None:
            print(f"KnowledgeService processing {path} with lane {lane}")

    class MockRepoService:
        def process(self, path: Path, lane: str) -> None:
            print(f"RepoService processing {path} with lane {lane}")

    # Instantiate services
    strategy_service = MockStrategyService()
    knowledge_service = MockKnowledgeService()
    repo_service = MockRepoService()

    # Instantiate router
    router = IngestRouter(strategy_service, knowledge_service, repo_service)

    # Simulate file paths from '~/takeout'
    takeout_path = Path.home() / "takeout"
    os.makedirs(takeout_path / "chat_services", exist_ok=True)
    os.makedirs(takeout_path / "docs", exist_ok=True)
    os.makedirs(takeout_path / "repos" / "my_project", exist_ok=True)
    os.makedirs(takeout_path / "notebooklm_export_1" / "source_documents", exist_ok=True)

    # Create some dummy files
    (takeout_path / "chat_services" / "my_chat.json").touch()
    (takeout_path / "docs" / "my_doc.pdf").touch()
    (takeout_path / "repos" / "my_project" / "main.py").touch()
    (takeout_path / "notebooklm_export_1" / "Note 1.txt").touch()


    # Test routing
    router.route(str(takeout_path / "chat_services" / "my_chat.json"))
    router.route(str(takeout_path / "docs" / "my_doc.pdf"))
    router.route(str(takeout_path / "repos" / "my_project" / "main.py"))
    router.route(str(takeout_path / "notebooklm_export_1"))
