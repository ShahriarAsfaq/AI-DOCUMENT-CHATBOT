import os
from pathlib import Path
from typing import List, Optional

from django.conf import settings

from .embeddings import EmbeddingService
from .vector_store import FaissVectorStore


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
