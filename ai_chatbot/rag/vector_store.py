"""Vector store implementation using FAISS for similarity search.

FAISS is loaded lazily at runtime to avoid container startup failures
if the package is not installed.
"""

import logging
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class FaissVectorStore:
    """FAISS-based vector store with runtime loading."""

    _faiss = None

    @classmethod
    def _get_faiss(cls):
        """Lazy load FAISS."""
        if cls._faiss is None:
            try:
                import faiss
                cls._faiss = faiss
                logger.info("FAISS loaded successfully.")
            except ImportError:
                logger.error("FAISS is not installed.")
                raise RuntimeError(
                    "FAISS library not installed. Install faiss-cpu to use vector search."
                )
        return cls._faiss

    def __init__(self):
        self.index = None
        self.metadata_list = []
        self.dimension = None
        self.document_metadata = {}

    def clear(self) -> None:
        self.index = None
        self.metadata_list = []
        self.dimension = None
        logger.info("Vector store cleared")

    def build_index(self, embeddings: np.ndarray, metadata: List[dict] = None) -> None:
        if embeddings is None or len(embeddings) == 0:
            raise ValueError("Embeddings array cannot be empty")

        faiss = self._get_faiss()

        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        n_vectors, dimension = embeddings.shape
        self.dimension = dimension

        if metadata:
            if len(metadata) != n_vectors:
                raise ValueError("Metadata length must match embeddings count")
            self.metadata_list = metadata.copy()
        else:
            self.metadata_list = [{} for _ in range(n_vectors)]

        logger.info(f"Building FAISS index with {n_vectors} vectors")

        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

        logger.info(f"FAISS index built with {self.index.ntotal} vectors")

    def save_index(self, path: str) -> None:
        if self.index is None:
            raise ValueError("Index not built")

        faiss = self._get_faiss()

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        index_file = path / "faiss.index"
        metadata_file = path / "metadata.pkl"

        faiss.write_index(self.index, str(index_file))

        with open(metadata_file, "wb") as f:
            pickle.dump(
                {
                    "metadata_list": self.metadata_list,
                    "dimension": self.dimension,
                    "document_metadata": self.document_metadata,
                },
                f,
            )

        logger.info("FAISS index saved")

    def load_index(self, path: str) -> None:
        faiss = self._get_faiss()

        path = Path(path)
        index_file = path / "faiss.index"
        metadata_file = path / "metadata.pkl"

        if not index_file.exists():
            raise FileNotFoundError(index_file)

        if not metadata_file.exists():
            raise FileNotFoundError(metadata_file)

        self.index = faiss.read_index(str(index_file))

        with open(metadata_file, "rb") as f:
            data = pickle.load(f)

        self.metadata_list = data.get("metadata_list", [])
        self.dimension = data.get("dimension")
        self.document_metadata = data.get("document_metadata", {})

        logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")

    def similarity_search(self, query_embedding: np.ndarray, k: int = 5) -> List[dict]:
        if self.index is None:
            raise ValueError("Index not built")

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.dtype != np.float32:
            query_embedding = query_embedding.astype(np.float32)

        distances, indices = self.index.search(query_embedding, k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.metadata_list):
                results.append(self.metadata_list[idx].copy())

        return results

    def similarity_search_with_score(
        self, query_embedding: np.ndarray, k: int = 5
    ) -> List[Tuple[dict, float]]:

        if self.index is None:
            raise ValueError("Index not built")

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.dtype != np.float32:
            query_embedding = query_embedding.astype(np.float32)

        distances, indices = self.index.search(query_embedding, k)

        results = []
        for idx, score in zip(indices[0], distances[0]):
            if 0 <= idx < len(self.metadata_list):
                results.append((self.metadata_list[idx].copy(), float(score)))

        return results

    def get_index_size(self) -> int:
        return 0 if self.index is None else self.index.ntotal

    def get_dimension(self) -> int:
        return self.dimension