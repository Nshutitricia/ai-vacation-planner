from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.services.knowledge_service import KnowledgeService


class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="What travel information to search for")


def create_knowledge_search_tool(session: Session) -> StructuredTool:
    knowledge_service = KnowledgeService()

    def _search(query: str) -> str:
        chunks = knowledge_service.search(query, session, top_k=3)
        if not chunks:
            return "No relevant travel knowledge found for this query."
        return "\n\n".join(chunk.content for chunk in chunks)

    return StructuredTool.from_function(
        func=_search,
        name="search_travel_knowledge",
        description=(
            "Search the curated travel knowledge base for travel guides, "
            "local tips, hidden gems, FAQs, and destination notes. Use "
            "this when you need specific, curated travel information "
            "beyond general knowledge."
        ),
        args_schema=KnowledgeSearchInput
    )
