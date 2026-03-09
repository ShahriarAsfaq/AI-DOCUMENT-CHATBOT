"""Text chunking module for document processing with validation.

Uses RecursiveCharacterTextSplitter for better chunking and includes
chunk validation to ensure meaningful content.
"""

import logging
from typing import List

from .document import Document

logger = logging.getLogger(__name__)


def split_into_chunks(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> List[Document]:
    """Split documents into smaller chunks with validation.

    Uses RecursiveCharacterTextSplitter for intelligent chunking.
    Validates chunks to ensure they contain meaningful content.

    Args:
        documents: list of Document objects to chunk.
        chunk_size: maximum size of each chunk in characters (default: 500).
        chunk_overlap: number of overlapping characters between consecutive
            chunks (default: 100).

    Returns:
        A list of Document instances representing the validated chunks.

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

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        # Initialize the text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],  # Prioritize natural breaks
            length_function=len,
        )

        chunks = []

        for doc in documents:
            text = doc.page_content.strip()
            if not text:
                logger.warning(f"Skipping empty document from {doc.metadata.get('source', 'unknown')}")
                continue

            # Split the document
            split_texts = text_splitter.split_text(text)

            logger.debug(f"Split document into {len(split_texts)} raw chunks")

            # Convert to Document objects and validate
            for i, chunk_text in enumerate(split_texts):
                # Validate chunk
                if _is_valid_chunk(chunk_text):
                    metadata = doc.metadata.copy()
                    metadata.update({
                        "chunk_index": i,
                        "chunk_start": i * (chunk_size - chunk_overlap),
                        "chunk_end": min((i + 1) * (chunk_size - chunk_overlap) + chunk_size, len(text)),
                    })

                    chunks.append(Document(
                        page_content=chunk_text,
                        metadata=metadata
                    ))
                else:
                    logger.debug(f"Discarded invalid chunk {i}: too short or empty")

        # Log sample chunks for verification
        if chunks:
            logger.info(f"Successfully created {len(chunks)} valid chunks")
            _log_chunk_samples(chunks[:min(10, len(chunks))])
        else:
            logger.warning("No valid chunks created from documents")

        return chunks

    except ImportError as e:
        logger.error(f"LangChain not available: {str(e)}. Using fallback chunker.")
        return _fallback_chunking(documents, chunk_size, chunk_overlap)
    except Exception as e:
        logger.error(f"Error splitting documents into chunks: {str(e)}")
        raise


def _is_valid_chunk(chunk_text: str) -> bool:
    """Validate if a chunk contains meaningful content.

    Args:
        chunk_text: The chunk text to validate.

    Returns:
        True if chunk is valid, False otherwise.
    """
    if not chunk_text or not isinstance(chunk_text, str):
        return False

    cleaned = chunk_text.strip()
    return len(cleaned) >= 20  # Minimum 20 characters for meaningful content


def _log_chunk_samples(chunks: List[Document]) -> None:
    """Log sample chunks for debugging and verification.

    Args:
        chunks: List of chunk documents to log.
    """
    logger.info("Sample chunks for verification:")
    for i, chunk in enumerate(chunks):
        text_preview = chunk.page_content[:100].replace('\n', ' ')
        metadata = chunk.metadata
        logger.info(
            f"  Chunk {i+1}: {len(chunk.page_content)} chars, "
            f"source='{metadata.get('source', 'unknown')}', "
            f"page={metadata.get('page', 'unknown')} - '{text_preview}...'"
        )


def _fallback_chunking(
    documents: List[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    """Fallback chunking method when LangChain is not available.

    Args:
        documents: List of documents to chunk.
        chunk_size: Maximum chunk size.
        chunk_overlap: Chunk overlap.

    Returns:
        List of chunk documents.
    """
    logger.warning("Using fallback character-based chunking")

    chunks = []

    for doc in documents:
        text = doc.page_content
        start = 0
        text_len = len(text)
        chunk_index = 0

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # Try to break at word boundaries
            if end < text_len and " " in text[start:end]:
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            chunk_text = text[start:end].strip()

            if _is_valid_chunk(chunk_text):
                metadata = doc.metadata.copy()
                metadata.update({
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": end,
                })

                chunks.append(Document(
                    page_content=chunk_text,
                    metadata=metadata
                ))
                chunk_index += 1

            # Move start forward
            start += chunk_size - chunk_overlap

    logger.info(f"Fallback chunking created {len(chunks)} valid chunks")
    return chunks
