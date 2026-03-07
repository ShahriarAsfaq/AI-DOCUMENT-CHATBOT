"""Embedding service for generating text embeddings.

Uses SentenceTransformer if available, otherwise falls back to lightweight mock implementation.
Automatic device detection (CPU/CUDA) and singleton pattern.
"""

import logging
from typing import List
import hashlib

import numpy as np

logger = logging.getLogger(__name__)


class MockEmbeddingService:
    """Lightweight mock embedding service that doesn't require torch/transformers."""

    def __init__(self, embedding_dim: int = 384):
        """Initialize mock embedding service.

        Args:
            embedding_dim: Dimension of embedding vectors (default: 384 to match SentenceTransformer)
        """
        self.embedding_dim = embedding_dim
        logger.info(f"Using MockEmbeddingService with dimension {embedding_dim}")

    def encode(self, texts: List[str], convert_to_numpy: bool = True) -> np.ndarray:
        """Generate mock embeddings based on text hash.

        Args:
            texts: List of texts to embed
            convert_to_numpy: Whether to convert to numpy (always True for mock)

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            raise ValueError("texts list cannot be empty")

        embeddings = []

        for text in texts:
            # Use hash-based deterministic embedding
            if not isinstance(text, str):
                text = str(text)

            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()

            # Create a deterministic but varied embedding from the hash
            embedding = np.zeros(self.embedding_dim, dtype=np.float32)

            # Use hash bytes to seed the embedding
            for i in range(0, len(hash_bytes), 4):
                chunk = hash_bytes[i : i + 4]
                value = int.from_bytes(chunk, byteorder="little") / (2**32)
                idx = i // 4
                if idx < self.embedding_dim:
                    embedding[idx] = (value - 0.5) * 2  # Range: -1 to 1

            # Normalize to unit vector
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            embeddings.append(embedding)

        return np.array(embeddings, dtype=np.float32)

    def get_sentence_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.embedding_dim


class EmbeddingService:
    """Singleton service for generating text embeddings.

    Uses sentence-transformers/all-MiniLM-L6-v2 model if available,
    otherwise falls back to MockEmbeddingService.
    """

    _instance = None
    _model = None
    _device = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize the model and device detection."""
        try:
            import torch

            cls._device = cls._detect_device()
            logger.info(f"Loading embedding model on device: {cls._device}")

            from sentence_transformers import SentenceTransformer

            cls._model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                device=cls._device,
            )
            logger.info(
                f"Embedding model loaded successfully. "
                f"Model dimension: {cls._model.get_sentence_embedding_dimension()}"
            )
        except (ImportError, Exception) as e:
            logger.warning(
                f"Could not load SentenceTransformer: {e}. Using MockEmbeddingService."
            )
            cls._model = MockEmbeddingService()
            cls._device = "cpu"

    @staticmethod
    def _detect_device() -> str:
        """Detect available device (CUDA or CPU).

        Returns:
            Device string: 'cuda' if CUDA is available, else 'cpu'.
        """
        try:
            import torch

            if torch.cuda.is_available():
                device = "cuda"
                logger.info(
                    f"CUDA detected. Using GPU: {torch.cuda.get_device_name(0)}"
                )
            else:
                device = "cpu"
                logger.info("No CUDA detected. Using CPU for embeddings.")
        except ImportError:
            device = "cpu"

        return device

    def encode(self, texts: List[str], convert_to_numpy: bool = True) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to encode.
            convert_to_numpy: Whether to convert to numpy array.

        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim).
            For the all-MiniLM-L6-v2 model, embedding_dim = 384.

        Raises:
            ValueError: If texts list is empty.
            Exception: For encoding failures.
        """
        if not texts:
            raise ValueError("texts list cannot be empty")

        if any(not isinstance(text, str) for text in texts):
            raise ValueError("All items in texts must be strings")

        try:
            logger.debug(f"Encoding {len(texts)} text(s) to embeddings")

            embeddings = self._model.encode(texts, convert_to_numpy=convert_to_numpy)

            # Ensure output is numpy
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings, dtype=np.float32)

            logger.debug(
                f"Successfully encoded {len(texts)} text(s). "
                f"Embedding shape: {embeddings.shape}"
            )

            return embeddings

        except Exception as e:
            logger.error(f"Error encoding texts: {str(e)}")
            raise Exception(f"Failed to encode texts: {str(e)}") from e

    def get_model_dimension(self) -> int:
        """Get the embedding dimension of the model.

        Returns:
            Integer representing embedding dimension (384 for all-MiniLM-L6-v2).
        """
        return self._model.get_sentence_embedding_dimension()

    def get_device(self) -> str:
        """Get the device the model is running on.

        Returns:
            Device string: 'cuda' or 'cpu'.
        """
        return self._device


# Convenience function to get singleton instance
def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton EmbeddingService instance.

    Returns:
        EmbeddingService instance.
    """
    return EmbeddingService()
