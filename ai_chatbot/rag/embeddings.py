"""Embedding service for generating text embeddings.

Uses SentenceTransformer for real embeddings. No mock fallbacks.
Automatic device detection (CPU/CUDA) and singleton pattern.
"""

import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton service for generating text embeddings using SentenceTransformer.

    Uses sentence-transformers/all-MiniLM-L6-v2 model.
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
            logger.error(f"Failed to load SentenceTransformer: {e}")
            logger.error("Cannot proceed without real embeddings. Install sentence-transformers and torch.")
            raise RuntimeError(f"Embedding service initialization failed: {e}")

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
            logger.warning("PyTorch not available. Using CPU for embeddings.")

        return device

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

            # Normalize embeddings for cosine similarity
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            embeddings = embeddings / norms

            logger.debug(
                f"Successfully encoded and normalized {len(texts)} text(s). "
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
