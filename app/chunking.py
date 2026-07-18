from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines())
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue

        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.extend(_split_long_text(current, chunk_size, overlap))
            current = paragraph

    if current:
        chunks.extend(_split_long_text(current, chunk_size, overlap))

    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)

    return pieces

