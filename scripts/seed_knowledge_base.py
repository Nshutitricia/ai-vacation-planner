import hashlib
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from src.database import engine
from src.services.knowledge_service import KnowledgeService
from src.utils.embeddings.chunker import chunk_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_source_files() -> list[tuple[str, str, str]]:
    files = []
    for category_dir in sorted(p for p in KNOWLEDGE_DIR.iterdir() if p.is_dir()):
        category = category_dir.name
        for file_path in sorted(category_dir.glob("*.md")):
            text = file_path.read_text(encoding="utf-8")
            files.append((file_path.name, category, text))
    return files


def seed() -> None:
    source_files = find_source_files()
    if not source_files:
        logger.warning(f"No knowledge files found under {KNOWLEDGE_DIR}. Nothing to seed.")
        return

    service = KnowledgeService()

    with Session(engine) as session:
        existing_hash_by_source = service.get_existing_hashes(session)

        current_sources = {source for source, _, _ in source_files}
        stale_sources = set(existing_hash_by_source) - current_sources
        if stale_sources:
            logger.info(f"Removing {len(stale_sources)} deleted file(s): {stale_sources}")
            service.remove_sources(stale_sources, session)

        records = []
        for source, category, text in source_files:
            content_hash = hash_content(text)
            if existing_hash_by_source.get(source) == content_hash:
                logger.info(f"Unchanged, skipping: {source}")
                continue

            logger.info(f"New or changed, re-embedding: {source}")
            records.append((source, category, content_hash, chunk_text(text)))

        embedded_count = service.reindex_sources(records, session)
        session.commit()

        if embedded_count:
            logger.info(f"Embedded {embedded_count} chunk(s) from {len(records)} file(s).")
        else:
            logger.info("Nothing new to embed.")


if __name__ == "__main__":
    seed()
