import re


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    pieces = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_by_sentence(paragraph, chunk_size))

    chunks = []
    current = ""

    for piece in pieces:
        if current and len(current) + len(piece) + 2 > chunk_size:
            chunks.append(current.strip())
            current = _overlap_tail(current, overlap) + "\n\n" + piece
        else:
            current = f"{current}\n\n{piece}" if current else piece

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _split_by_sentence(paragraph: str, chunk_size: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)

    pieces = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > chunk_size:
            pieces.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence

    if current.strip():
        pieces.append(current.strip())

    return pieces


def _overlap_tail(text: str, overlap: int) -> str:

    if overlap <= 0:
        return ""
    tail = text[-overlap:]
    space_index = tail.find(" ")
    if space_index != -1:
        tail = tail[space_index + 1:]
    return tail
