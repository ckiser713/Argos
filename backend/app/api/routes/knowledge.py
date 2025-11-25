from typing import List

from fastapi import APIRouter

from app.domain.models import KnowledgeNode, KnowledgeSearchRequest
from app.services.knowledge_service import knowledge_service

router = APIRouter()


@router.get("/nodes", response_model=List[KnowledgeNode], summary="List knowledge nodes")
def list_knowledge_nodes() -> List[KnowledgeNode]:
    return knowledge_service.list_nodes()


@router.post("/search", response_model=List[KnowledgeNode], summary="Search knowledge nodes")
def search_knowledge(request: KnowledgeSearchRequest) -> List[KnowledgeNode]:
    return knowledge_service.search(request)
