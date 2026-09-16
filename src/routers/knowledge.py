from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from src.database import get_session
from src.models.user import User
from src.models.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult
from src.services.knowledge_service import KnowledgeService
from src.utils.deps import get_current_user

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

knowledge_service = KnowledgeService()


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    query: str = Query(..., min_length=1, description="What to search the travel knowledge base for"),
    top_k: int = Query(5, ge=1, le=20, description="Maximum number of results to return"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    chunks = knowledge_service.search(query, session, top_k=top_k)
    return KnowledgeSearchResponse(
        query=query,
        results=[
            KnowledgeSearchResult(
                source=chunk.source,
                category=chunk.category,
                content=chunk.content
            )
            for chunk in chunks
        ]
    )
