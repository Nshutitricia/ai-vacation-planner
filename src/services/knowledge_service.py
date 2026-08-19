from sqlmodel import Session, select, delete
from src.models.knowledge import KnowledgeChunk
from src.embeddings.embedder import VoyageEmbedder


class KnowledgeService:
    # Cosine distance cutoff below which a chunk counts as actually
    # relevant. Picked empirically: genuinely relevant queries against
    # this knowledge base scored 0.33-0.44, while clearly unrelated
    # queries (a destination/topic with no matching content) scored
    # 0.53 and up. 0.5 sits cleanly in the gap between the two.
    DEFAULT_MAX_DISTANCE = 0.5

    def __init__(self):
        self.embedder = VoyageEmbedder()

    def search(
        self,
        query: str,
        session: Session,
        top_k: int = 5,
        max_distance: float = DEFAULT_MAX_DISTANCE
    ) -> list[KnowledgeChunk]:
        """
        Return up to top_k chunks semantically similar to the query,
        excluding any whose distance exceeds max_distance — so a query
        with no genuinely relevant content in the knowledge base
        returns an empty list instead of the "closest available"
        chunks regardless of how unrelated they actually are.
        """
        query_vector = self.embedder.embed_query(query)
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
        rows = session.exec(
            select(KnowledgeChunk, distance.label("distance"))
            .order_by(distance)
            .limit(top_k)
        ).all()
        return [chunk for chunk, dist in rows if dist <= max_distance]

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
