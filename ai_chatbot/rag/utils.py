import os
from pathlib import Path
from typing import List, Optional

from django.conf import settings

from .embeddings import EmbeddingService
from .vector_store import FaissVectorStore


def generate_document_summary(full_text: str, llm_service) -> str:
    """Generate a concise 5‑sentence summary for the given text using the provided LLM service.

    Args:
        full_text: The complete text of the document.
        llm_service: An LLM service instance with a `generate()` method.

    Returns:
        Generated summary string.
    """
    # simple deterministic prompt for summary
    prompt = (
        "Please provide a concise summary of the following document text in about 5 sentences."
        "\n\n" + full_text
    )
    try:
        summary = llm_service.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt=prompt,
            temperature=0.0,
            do_sample=False,
            max_tokens=500,
        )
    except Exception as e:
        # fallback to empty string on failure
        summary = ""
    return summary.strip()


def extract_document_topics(full_text: str, llm_service) -> list:
    """Extract main topics from document text using the LLM service.

    The returned list contains up to 10 topics extracted as clean bullet points.
    """
    prompt = (
        "Identify the main topics discussed in this document. "
        "Return a clean bullet list (maximum 10 topics)."
        "\n\n" + full_text
    )
    try:
        raw = llm_service.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt=prompt,
            temperature=0.0,
            do_sample=False,
            max_tokens=200,
        )
    except Exception as e:
        return []

    topics = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        # strip common bullet characters
        if text[0] in ['-', '*', '•']:
            text = text[1:].strip()
        if text:
            topics.append(text)
        if len(topics) >= 10:
            break
    return topics


def get_vector_store(texts: List[str], metadata: Optional[List[dict]] = None, persist: bool = True) -> FaissVectorStore:
    """Create a FAISS vector store from given texts.

    Args:
        texts: list of strings to index.
        metadata: optional list of metadata dictionaries (same length as texts).
        persist: whether to save the index to disk (at VECTOR_STORE_PATH/faiss_store).

    Returns:
        An initialized FaissVectorStore instance containing the embeddings.
    """
    if not texts:
        raise ValueError("texts list cannot be empty")

    # compute embeddings using the local embedding service
    embed_service = EmbeddingService()
    embeddings = embed_service.encode(texts)

    store = FaissVectorStore()
    store.build_index(embeddings, metadata or [{} for _ in texts])

    if persist:
        db_path = Path(settings.VECTOR_STORE_PATH) / "faiss_store"
        os.makedirs(db_path, exist_ok=True)
        store.save_index(str(db_path))

    return store
