"""
Chat history parser service for extracting project ideas and code from chat exports.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.model_lanes import ModelLane
from app.services.llm_service import generate_text

logger = logging.getLogger(__name__)


class ChatParserService:
    """
    Service for parsing chat export files and extracting project ideas, code snippets, and technical discussions.
    """

    def __init__(self):
        self.code_block_pattern = re.compile(r"```(?:[\w]+)?\n(.*?)```", re.DOTALL)
        self.json_pattern = re.compile(r"\{.*\}", re.DOTALL)

    def parse_chat_export(
        self,
        file_path: str,
        project_id: str,
        format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse a chat export file and extract structured information.

        Args:
            file_path: Path to the chat export file
            project_id: Project ID to associate extracted ideas with
            format: File format (json, markdown, csv) - auto-detected if None

        Returns:
            Dictionary with parsed data including ideas, code snippets, and conversations
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Chat export file not found: {file_path}")

        # Auto-detect format
        if not format:
            format = self._detect_format(path)

        logger.info(f"Parsing chat export: {file_path} (format: {format})")

        try:
            if format == "json":
                return self._parse_json(path, project_id)
            elif format == "markdown":
                return self._parse_markdown(path, project_id)
            elif format == "csv":
                return self._parse_csv(path, project_id)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Failed to parse chat export: {e}")
            raise

    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension."""
        ext = path.suffix.lower()
        if ext == ".json":
            return "json"
        elif ext in [".md", ".markdown"]:
            return "markdown"
        elif ext == ".csv":
            return "csv"
        else:
            # Try to detect from content
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline()
                if first_line.strip().startswith("{"):
                    return "json"
                elif first_line.strip().startswith("#"):
                    return "markdown"
                elif "," in first_line:
                    return "csv"
            return "markdown"  # Default fallback

    def _parse_json(self, path: Path, project_id: str) -> Dict[str, Any]:
        """Parse JSON chat export."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle different JSON structures
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict):
            # Common formats: {"messages": [...]} or {"conversations": [...]}
            messages = data.get("messages", data.get("conversations", []))
        else:
            raise ValueError("Invalid JSON structure")

        return self._extract_from_messages(messages, project_id)

    def _parse_markdown(self, path: Path, project_id: str) -> Dict[str, Any]:
        """Parse Markdown chat export."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract messages from markdown (simple heuristic)
        messages = []
        lines = content.split("\n")
        current_message = None

        for line in lines:
            # Look for user/assistant markers
            if line.startswith("## User:") or line.startswith("### User:"):
                if current_message:
                    messages.append(current_message)
                current_message = {"role": "user", "content": line.replace("## User:", "").replace("### User:", "").strip()}
            elif line.startswith("## Assistant:") or line.startswith("### Assistant:") or line.startswith("## AI:"):
                if current_message:
                    messages.append(current_message)
                current_message = {"role": "assistant", "content": line.replace("## Assistant:", "").replace("### Assistant:", "").replace("## AI:", "").strip()}
            elif current_message:
                current_message["content"] += "\n" + line

        if current_message:
            messages.append(current_message)

        return self._extract_from_messages(messages, project_id)

    def _parse_csv(self, path: Path, project_id: str) -> Dict[str, Any]:
        """Parse CSV chat export."""
        import csv

        messages = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Common CSV columns: role, content, timestamp, etc.
                role = row.get("role", row.get("sender", "user"))
                content = row.get("content", row.get("message", ""))
                if content:
                    messages.append({"role": role.lower(), "content": content})

        return self._extract_from_messages(messages, project_id)

    def _extract_from_messages(
        self,
        messages: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, Any]:
        """Extract ideas, code, and conversations from message list."""
        ideas = []
        code_snippets = []
        conversations = []

        for i, msg in enumerate(messages):
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")

            if not content:
                continue

            # Extract code blocks
            code_blocks = self.code_block_pattern.findall(content)
            for code in code_blocks:
                code_snippets.append({
                    "code": code.strip(),
                    "context": content[:200],  # First 200 chars for context
                    "message_index": i,
                    "role": role,
                })

            # Classify message as chit-chat vs project idea using LLM
            is_project_idea = self._classify_message(content, role)

            if is_project_idea:
                ideas.append({
                    "text": content,
                    "role": role,
                    "message_index": i,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                })

            # Store conversation for searchability
            conversations.append({
                "role": role,
                "content": content,
                "index": i,
            })

        return {
            "project_id": project_id,
            "ideas": ideas,
            "code_snippets": code_snippets,
            "conversations": conversations,
            "total_messages": len(messages),
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _classify_message(self, content: str, role: str) -> bool:
        """
        Classify a message as project idea/code vs chit-chat.
        Uses LLM for classification with fallback heuristics.
        """
        # Heuristic: messages with code blocks are likely project-related
        if self.code_block_pattern.search(content):
            return True

        # Heuristic: messages mentioning technical terms
        technical_keywords = [
            "implement", "build", "create", "design", "architecture",
            "function", "class", "api", "database", "server", "client",
            "feature", "bug", "fix", "refactor", "test", "deploy",
        ]
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in technical_keywords):
            return True

        # Use LLM for more nuanced classification (if available)
        try:
            prompt = f"""Classify the following message as either:
1. PROJECT_IDEA - Contains project ideas, code discussions, technical plans, or actionable items
2. CHIT_CHAT - General conversation, greetings, or non-technical discussion

Message (from {role}):
{content[:500]}

Respond with only: PROJECT_IDEA or CHIT_CHAT"""

            response = generate_text(
                prompt,
                project_id="system",  # Use system project for classification
                lane=ModelLane.ORCHESTRATOR,
                temperature=0.1,
                max_tokens=10,
            )

            return "PROJECT_IDEA" in response.response.upper()
        except Exception as e:
            logger.warning(f"LLM classification failed, using heuristic: {e}")
            # Fallback to heuristic
            return len(content) > 50 and any(keyword in content_lower for keyword in technical_keywords)

    def link_to_projects(
        self,
        parsed_data: Dict[str, Any],
        existing_projects: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Link extracted ideas to existing projects based on semantic similarity.
        """
        linked_ideas = []
        for idea in parsed_data.get("ideas", []):
            # Simple keyword matching for now
            # In production, use embeddings for semantic matching
            idea_text = idea["text"].lower()
            best_match = None
            best_score = 0

            for project in existing_projects:
                project_name = project.get("name", "").lower()
                project_desc = project.get("description", "").lower()

                # Simple scoring
                score = 0
                if project_name in idea_text:
                    score += 2
                if project_desc and project_desc in idea_text:
                    score += 1

                if score > best_score:
                    best_score = score
                    best_match = project

            if best_match and best_score > 0:
                idea["linked_project_id"] = best_match["id"]
                idea["link_confidence"] = best_score / 3.0  # Normalize to 0-1

            linked_ideas.append(idea)

        parsed_data["ideas"] = linked_ideas
        return parsed_data


chat_parser_service = ChatParserService()
