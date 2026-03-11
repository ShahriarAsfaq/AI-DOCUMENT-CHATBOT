"""Embedding service for generating text embeddings at runtime.

Heavy ML packages (torch, sentence-transformers) are loaded lazily
to keep Docker image small.
"""

import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Singleton service for generating text embeddings lazily."""

    _instance = None
    _model = None
    _device = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _initialize(self):
        """Lazy load model when first needed."""
        if self._initialized:
            return

        try:
            import torch
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Device detected for embeddings: {self._device}")

            from sentence_transformers import SentenceTransformer

            logger.info("Downloading/loading embedding model at runtime...")
            self._model = SentenceTransformer(
                "sentence-transformers/paraphrase-MiniLM-L3-v2",
                device=self._device,
            )
            logger.info(
                f"Model loaded. Embedding dimension: {self._model.get_sentence_embedding_dimension()}"
            )
            self._initialized = True
        except ImportError:
            logger.error(
                "torch or sentence-transformers not installed. "
                "Embeddings cannot be generated."
            )
            raise RuntimeError(
                "Install sentence-transformers and torch to use embeddings."
            )
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Embedding initialization failed: {e}")

    def encode(self, texts: List[str], convert_to_numpy: bool = True) -> np.ndarray:
        """Encode texts to embeddings lazily."""
        if not texts:
            raise ValueError("texts list cannot be empty")
        if any(not isinstance(text, str) for text in texts):
            raise ValueError("All items in texts must be strings")

        # Initialize model on first request
        if self._model is None:
            self._initialize()

        try:
            embeddings = self._model.encode(texts, convert_to_numpy=convert_to_numpy)
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings, dtype=np.float32)

            # Normalize
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            embeddings = embeddings / norms
            return embeddings
        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise

    def get_model_dimension(self) -> int:
        if self._model is None:
            self._initialize()
        return self._model.get_sentence_embedding_dimension()

    def get_device(self) -> str:
        if self._device is None:
            self._initialize()
        return self._device


# Singleton accessor
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()