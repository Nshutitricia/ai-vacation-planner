from sqlmodel import Session, select, delete
from src.models.knowledge import KnowledgeChunk
from src.utils.embeddings.embedder import VoyageEmbedder


class KnowledgeService:
    def __init__(self):
        self.embedder = VoyageEmbedder()

    def search(self, query: str, session: Session, top_k: int = 5) -> list[KnowledgeChunk]:
        query_vector = self.embedder.embed_query(query)
        return session.exec(
            select(KnowledgeChunk)
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
        ).all()

    def get_existing_hashes(self, session: Session) -> dict[str, str]:
        rows = session.exec(
            select(KnowledgeChunk.source, KnowledgeChunk.content_hash)
        ).all()
        return dict(rows)

    def remove_sources(self, sources: set[str], session: Session) -> None:
        if not sources:
            return
        session.exec(delete(KnowledgeChunk).where(KnowledgeChunk.source.in_(sources)))

    def reindex_sources(
        self,
        records: list[tuple[str, str, str, list[str]]],
        session: Session
    ) -> int:
        if not records:
            return 0

        sources = [source for source, _, _, _ in records]
        self.remove_sources(set(sources), session)

        flat_chunks = []
        chunk_meta = []
        for source, category, content_hash, chunks in records:
            for chunk in chunks:
                flat_chunks.append(chunk)
                chunk_meta.append((source, category, content_hash))

        vectors = self.embedder.embed_documents(flat_chunks)

        for (source, category, content_hash), chunk, vector in zip(chunk_meta, flat_chunks, vectors):
            session.add(KnowledgeChunk(
                content=chunk,
                source=source,
                category=category,
                content_hash=content_hash,
                embedding=vector,
            ))

        return len(flat_chunks)
