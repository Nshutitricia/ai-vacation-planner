import logging

import voyageai

from src.config import settings

logger = logging.getLogger(__name__)


class VoyageEmbedder:

    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.model = settings.EMBEDDING_MODEL

    def embed_documents(self, texts: list[str]) -> list[list[float]]:

        logger.info(f"Embedding {len(texts)} document chunk(s) with {self.model}")
        result = self.client.embed(
            texts,
            model=self.model,
            input_type="document"
        )
        return result.embeddings

    def embed_query(self, text: str) -> list[float]:

        result = self.client.embed(
            [text],
            model=self.model,
            input_type="query"
        )
        return result.embeddings[0]
