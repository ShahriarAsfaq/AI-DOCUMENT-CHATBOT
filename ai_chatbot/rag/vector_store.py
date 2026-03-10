"""Vector store implementation using FAISS for similarity search.

Provides persistent storage and retrieval of embeddings with metadata mapping.
"""

import logging
import pickle
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

logger = logging.getLogger(__name__)


class FaissVectorStore:
    """FAISS-based vector store for efficient similarity search.

    Stores embeddings in a FAISS index and maintains metadata mapping
    for retrieval of original chunks and documents.  Also optionally holds
    document-level metadata (summary/topics/chunks) for intent-based answers.
    """

    def __init__(self):
        """Initialize the vector store."""
        self.index = None
        self.metadata_list = []  # List of metadata dicts corresponding to index vectors
        self.dimension = None
        # additional data attached at build time
        self.document_metadata = {}

    def clear(self) -> None:
        """Clear the vector store, resetting it to empty state."""
        self.index = None
        self.metadata_list = []
        self.dimension = None
        logger.info("Vector store cleared")

    def build_index(self, embeddings: np.ndarray, metadata: List[dict] = None) -> None:
        """Build a FAISS index from embeddings.

        Args:
            embeddings: numpy array of shape (n_vectors, embedding_dim).
            metadata: Optional list of metadata dicts corresponding to each embedding.
                     If provided, must have same length as embeddings.

        Raises:
            ValueError: If embeddings is empty or metadata length mismatch.
            Exception: For index building failures.
        """
        if embeddings is None or len(embeddings) == 0:
            raise ValueError("Embeddings array cannot be empty")

        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        n_vectors, dimension = embeddings.shape
        self.dimension = dimension

        if metadata is not None:
            if len(metadata) != n_vectors:
                raise ValueError(
                    f"Metadata length ({len(metadata)}) must match "
                    f"embeddings count ({n_vectors})"
                )
            self.metadata_list = metadata.copy()
        else:
            self.metadata_list = [{} for _ in range(n_vectors)]

        try:
            logger.info(
                f"Building FAISS index with {n_vectors} vectors "
                f"of dimension {dimension}"
            )

            # Create IndexFlatIP (cosine similarity with normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(embeddings)

            logger.info(
                f"Successfully built FAISS index. "
                f"Index contains {self.index.ntotal} vectors"
            )

        except Exception as e:
            logger.error(f"Error building FAISS index: {str(e)}")
            raise Exception(f"Failed to build FAISS index: {str(e)}") from e

    def save_index(self, path: str) -> None:
        """Save the FAISS index and metadata to disk.

        Args:
            path: Directory path to save index files.

        Raises:
            ValueError: If index has not been built.
            Exception: For save operation failures.
        """
        if self.index is None:
            raise ValueError("Index has not been built. Call build_index() first.")

        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)

            index_file = path / "faiss.index"
            metadata_file = path / "metadata.pkl"

            # Save FAISS index
            faiss.write_index(self.index, str(index_file))
            logger.info(f"Saved FAISS index to {index_file}")

            # Save metadata mapping
            with open(metadata_file, "wb") as f:
                pickle.dump(
                    {
                        "metadata_list": self.metadata_list,
                        "dimension": self.dimension,
                        "document_metadata": getattr(self, "document_metadata", {}),
                    },
                    f,
                )
            logger.info(f"Saved metadata to {metadata_file}")

        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
            raise Exception(f"Failed to save FAISS index: {str(e)}") from e

    def load_index(self, path: str) -> None:
        """Load FAISS index and metadata from disk.

        Args:
            path: Directory path containing index files (faiss.index, metadata.pkl).

        Raises:
            FileNotFoundError: If index files do not exist.
            Exception: For load operation failures.
        """
        try:
            path = Path(path)
            index_file = path / "faiss.index"
            metadata_file = path / "metadata.pkl"

            if not index_file.exists():
                raise FileNotFoundError(f"Index file not found: {index_file}")

            if not metadata_file.exists():
                raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            logger.info(
                f"Loaded FAISS index from {index_file}. "
                f"Contains {self.index.ntotal} vectors"
            )

            # Load metadata
            with open(metadata_file, "rb") as f:
                data = pickle.load(f)
                self.metadata_list = data.get("metadata_list", [])
                self.dimension = data.get("dimension")
                # restore optional document metadata
                self.document_metadata = data.get("document_metadata", {})

            logger.info(f"Loaded metadata from {metadata_file}")

        except FileNotFoundError:
            raise
    def reload_index(self, path: str) -> None:
        """Reload the FAISS index and metadata from disk.

        This is useful when the index files have been updated externally.

        Args:
            path: Directory path containing index files (faiss.index, metadata.pkl).

        Raises:
            FileNotFoundError: If index files do not exist.
            Exception: For load operation failures.
        """
        try:
            path = Path(path)
            index_file = path / "faiss.index"
            metadata_file = path / "metadata.pkl"

            if not index_file.exists():
                raise FileNotFoundError(f"Index file not found: {index_file}")

            if not metadata_file.exists():
                raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            logger.info(
                f"Reloaded FAISS index from {index_file}. "
                f"Contains {self.index.ntotal} vectors"
            )

            # Load metadata
            with open(metadata_file, "rb") as f:
                data = pickle.load(f)
                self.metadata_list = data["metadata_list"]
                self.dimension = data["dimension"]
                # restore optional document metadata when reloading
                self.document_metadata = data.get("document_metadata", {})

            logger.info(f"Reloaded metadata from {metadata_file}")

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error reloading index: {str(e)}")
            raise Exception(f"Failed to reload FAISS index: {str(e)}") from e

    def similarity_search(
        self, query_embedding: np.ndarray, k: int = 5
    ) -> List[dict]:
        """Search for k most similar vectors.

        Args:
            query_embedding: Query vector of shape (embedding_dim,) or (1, embedding_dim).
            k: Number of results to return.

        Returns:
            List of metadata dicts for k most similar vectors, ordered by similarity.

        Raises:
            ValueError: If index not built or query dimension mismatch.
            Exception: For search failures.
        """
        if self.index is None:
            raise ValueError("Index has not been built or loaded.")

        try:
            # Reshape if needed
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            if query_embedding.dtype != np.float32:
                query_embedding = query_embedding.astype(np.float32)

            if query_embedding.shape[1] != self.dimension:
                raise ValueError(
                    f"Query dimension ({query_embedding.shape[1]}) does not match "
                    f"index dimension ({self.dimension})"
                )

            # Search
            distances, indices = self.index.search(query_embedding, k)

            # Extract metadata for returned indices
            results = []
            for idx in indices[0]:
                if 0 <= idx < len(self.metadata_list):
                    results.append(self.metadata_list[idx].copy())
                else:
                    logger.warning(f"Invalid index {idx} returned by FAISS search")

            logger.debug(f"Similarity search returned {len(results)} result(s)")
            return results

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            raise Exception(f"Failed to perform similarity search: {str(e)}") from e

    def similarity_search_with_score(
        self, query_embedding: np.ndarray, k: int = 5
    ) -> List[Tuple[dict, float]]:
        """Search for k most similar vectors with scores.

        Args:
            query_embedding: Query vector of shape (embedding_dim,) or (1, embedding_dim).
            k: Number of results to return.

        Returns:
            List of (metadata_dict, score) tuples for k most similar vectors,
            ordered by similarity (lower score = more similar).

        Raises:
            ValueError: If index not built or query dimension mismatch.
            Exception: For search failures.
        """
        if self.index is None:
            raise ValueError("Index has not been built or loaded.")

        try:
            # Reshape if needed
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            if query_embedding.dtype != np.float32:
                query_embedding = query_embedding.astype(np.float32)

            if query_embedding.shape[1] != self.dimension:
                raise ValueError(
                    f"Query dimension ({query_embedding.shape[1]}) does not match "
                    f"index dimension ({self.dimension})"
                )

            # Search
            distances, indices = self.index.search(query_embedding, k)

            # Extract metadata and scores for returned indices
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if 0 <= idx < len(self.metadata_list):
                    metadata = self.metadata_list[idx]

                    # Validate chunk_text exists and is not empty
                    chunk_text = metadata.get('chunk_text', '').strip()
                    if not chunk_text:
                        logger.warning(f"Skipping chunk with empty chunk_text: {metadata}")
                        continue

                    results.append((metadata, float(distance)))
                else:
                    logger.warning(f"Invalid index {idx} returned by FAISS search")

            logger.debug(f"Similarity search returned {len(results)} valid results")
            return results

        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise Exception(f"Failed to perform similarity search: {str(e)}") from e
        if self.index is None:
            raise ValueError("Index has not been built or loaded.")

        try:
            # Reshape if needed
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            if query_embedding.dtype != np.float32:
                query_embedding = query_embedding.astype(np.float32)

            if query_embedding.shape[1] != self.dimension:
                raise ValueError(
                    f"Query dimension ({query_embedding.shape[1]}) does not match "
                    f"index dimension ({self.dimension})"
                )

            # Search
            similarities, indices = self.index.search(query_embedding, k)

            # Pair metadata with similarities
            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                if 0 <= idx < len(self.metadata_list):
                    results.append((self.metadata_list[idx].copy(), float(sim)))

            logger.debug(
                f"Similarity search with scores returned {len(results)} result(s)"
            )
            return results

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error during similarity search with score: {str(e)}")
            raise Exception(
                f"Failed to perform similarity search with score: {str(e)}"
            ) from e

    def get_index_size(self) -> int:
        """Get the number of vectors in the index.

        Returns:
            Number of vectors in the index, or 0 if index not built.
        """
        if self.index is None:
            return 0
        return self.index.ntotal

    def get_dimension(self) -> int:
        """Get the embedding dimension.

        Returns:
            Embedding dimension, or None if index not built.
        """
        return self.dimension
