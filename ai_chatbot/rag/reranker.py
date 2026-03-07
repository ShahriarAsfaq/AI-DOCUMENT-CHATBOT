"""Re-ranker for improving search result relevance.

Uses cross-encoder for more accurate relevance scoring than similarity distance.
"""

import logging
from typing import List, Tuple

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class RerankerService:
    """Cross-encoder based re-ranker for search results.

    Uses ms-marco-MiniLM-L-6-v2 cross-encoder for improved relevance ranking.
    """

    _instance = None
    _model = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize the cross-encoder model."""
        logger.info("Loading cross-encoder model for re-ranking")

        try:
            cls._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {str(e)}")
            raise

    def rerank(
        self,
        question: str,
        candidate_texts: List[str],
        top_k: int = 5,
    ) -> List[str]:
        """Re-rank candidate texts by relevance to question.

        Uses cross-encoder to score question-text pairs and returns
        top_k most relevant texts, sorted by score (descending).

        Args:
            question: Query or question string.
            candidate_texts: List of candidate text passages to rank.
            top_k: Number of top results to return.

        Returns:
            List of top_k candidate texts sorted by relevance score (best first).
            If re-ranking fails, returns original candidates (up to top_k).

        Raises:
            ValueError: If inputs are invalid.
        """
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")

        if not candidate_texts or not isinstance(candidate_texts, list):
            raise ValueError("candidate_texts must be a non-empty list")

        if top_k <= 0:
            raise ValueError("top_k must be positive")

        try:
            logger.info(
                f"Re-ranking {len(candidate_texts)} candidate(s) "
                f"for question: '{question[:50]}...'"
            )

            # Prepare question-text pairs
            pairs = [[question, text] for text in candidate_texts]

            # Score all pairs
            scores = self._model.predict(pairs)

            # Create list of (text, score) tuples
            scored_results = list(zip(candidate_texts, scores))

            # Sort by score (descending)
            scored_results.sort(key=lambda x: x[1], reverse=True)

            # Extract top_k texts
            top_results = [text for text, score in scored_results[:top_k]]

            logger.info(
                f"Re-ranking complete. Returned {len(top_results)} result(s). "
                f"Top score: {scored_results[0][1]:.4f}"
            )

            return top_results

        except Exception as e:
            logger.warning(
                f"Error during re-ranking: {str(e)}. "
                f"Returning original candidates."
            )
            # Fallback: return original candidates up to top_k
            return candidate_texts[:top_k]

    def rerank_with_scores(
        self,
        question: str,
        candidate_texts: List[str],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Re-rank candidate texts and return scores.

        Args:
            question: Query or question string.
            candidate_texts: List of candidate text passages to rank.
            top_k: Number of top results to return.

        Returns:
            List of (text, score) tuples sorted by score (descending).
            If re-ranking fails, returns candidates with score 0.0.

        Raises:
            ValueError: If inputs are invalid.
        """
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")

        if not candidate_texts or not isinstance(candidate_texts, list):
            raise ValueError("candidate_texts must be a non-empty list")

        if top_k <= 0:
            raise ValueError("top_k must be positive")

        try:
            logger.info(
                f"Re-ranking with scores for {len(candidate_texts)} candidate(s)"
            )

            # Prepare question-text pairs
            pairs = [[question, text] for text in candidate_texts]

            # Score all pairs
            scores = self._model.predict(pairs)

            # Create list of (text, score) tuples
            scored_results = list(zip(candidate_texts, scores))

            # Sort by score (descending)
            scored_results.sort(key=lambda x: x[1], reverse=True)

            # Return top_k with scores
            top_results = scored_results[:top_k]

            logger.info(
                f"Re-ranking complete. Returned {len(top_results)} result(s) with scores."
            )

            return top_results

        except Exception as e:
            logger.warning(
                f"Error during re-ranking with scores: {str(e)}. "
                f"Returning candidates with 0.0 scores."
            )
            # Fallback: return candidates with 0.0 score
            return [(text, 0.0) for text in candidate_texts[:top_k]]


def get_reranker_service() -> RerankerService:
    """Get or create the singleton RerankerService instance.

    Returns:
        RerankerService instance.
    """
    return RerankerService()
