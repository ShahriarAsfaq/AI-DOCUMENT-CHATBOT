"""Text chunking module for document processing.

Splits documents into smaller chunks while preserving metadata.
This version does not depend on LangChain and uses a straightforward
character-based splitter with optional overlap.
"""

import logging
from typing import List

from .document import Document

logger = logging.getLogger(__name__)


def split_into_chunks(
    documents: List[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 200,
) -> List[Document]:
    """Split documents into smaller chunks with overlap.

    Args:
        documents: list of Document objects to chunk.
        chunk_size: maximum size of each chunk in characters.
        chunk_overlap: number of overlapping characters between consecutive
            chunks (defaults to 200).

    Returns:
        A list of Document instances representing the chunks.

    Raises:
        ValueError: if input list is empty or parameters invalid.
    """

    if not documents:
        raise ValueError("Documents list cannot be empty")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    logger.info(
        f"Splitting {len(documents)} document(s) into chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )

    chunks: List[Document] = []

    try:
        for doc in documents:
            text = doc.page_content
            start = 0
            text_len = len(text)
            while start < text_len:
                end = min(start + chunk_size, text_len)
                # avoid cutting mid-word if possible
                if end < text_len and " " in text[start:end]:
                    # backtrack to last space
                    last_space = text.rfind(" ", start, end)
                    if last_space > start:
                        end = last_space
                chunk_text = text[start:end]
                metadata = doc.metadata.copy() if isinstance(doc.metadata, dict) else {}
                metadata.update({"chunk_start": start, "chunk_end": end})
                chunks.append(Document(page_content=chunk_text, metadata=metadata))
                # move start forward by chunk_size - overlap
                start += chunk_size - chunk_overlap

        logger.info(f"Successfully created {len(chunks)} chunks from {len(documents)} document(s)")
        if chunks:
            sample = chunks[0]
            logger.debug(
                f"Sample chunk metadata: {sample.metadata}, "
                f"length: {len(sample.page_content)}"
            )
        return chunks
    except Exception as e:
        logger.error(f"Error splitting documents into chunks: {str(e)}")
        raise
