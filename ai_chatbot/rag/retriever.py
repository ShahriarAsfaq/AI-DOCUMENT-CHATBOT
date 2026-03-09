"""Retriever service for RAG-based document retrieval.

Orchestrates query expansion, embedding, vector search, and optional reranking.
"""

import logging
from typing import List, Tuple, Optional

from ai_chatbot.rag.query_expansion import generate_dynamic_search_queries
from ai_chatbot.rag.embeddings import get_embedding_service
from ai_chatbot.rag.vector_store import FaissVectorStore
from ai_chatbot.rag.reranker import get_reranker_service

logger = logging.getLogger(__name__)


class RetrieverService:
    """Service for retrieving relevant document chunks using FAISS + embeddings.

    Combines query expansion, embedding, vector search, and optional reranking
    to retrieve the most relevant chunks for a given question.
    """

    def __init__(
        self,
        vector_store: FaissVectorStore,
        use_reranking: bool = True,
        top_k: int = 10,
        num_query_variations: int = 5,
    ):
        """Initialize the retriever service.

        Args:
            vector_store: Built FaissVectorStore instance.
            use_reranking: Whether to apply cross-encoder reranking. Default: True
            top_k: Number of top results to return. Default: 3
            num_query_variations: Max query variations to generate. Default: 5
        """
        self.vector_store = vector_store
        self.use_reranking = use_reranking
        self.top_k = top_k
        self.num_query_variations = num_query_variations

        self.embedding_service = get_embedding_service()

        if use_reranking:
            self.reranker = get_reranker_service()
        else:
            self.reranker = None

        logger.info(
            f"RetrieverService initialized. "
            f"Reranking: {use_reranking}, Top-K: {top_k}"
        )

    def retrieve(self, question: str) -> List[Tuple[dict, float]]:
        """Retrieve relevant chunks for a question.

        Pipeline:
        1. Generate expanded query variations
        2. Embed each query
        3. Perform similarity search for each
        4. Combine and deduplicate results
        5. Optionally rerank using cross-encoder
        6. Return top_k chunks with scores

        Args:
            question: User question or query.

        Returns:
            List of (metadata_dict, score) tuples for top_k chunks.
            Metadata contains: page, source, and chunk_id.
            Score is similarity distance (lower is better).

        Raises:
            ValueError: If question is invalid.
            Exception: For retrieval failures.
        """
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")

        if self.vector_store.get_index_size() == 0:
            raise ValueError(
                "Vector store is empty. Build index before retrieving."
            )

        try:
            logger.info(f"Retrieving chunks for question: '{question[:60]}...'")

            # Step 1: Generate query variations
            logger.info("Step 1: Generating query variations...")
            expanded_queries = generate_dynamic_search_queries(question)
            logger.info(f"Generated {len(expanded_queries)} query variation(s): {[q[:30] + '...' for q in expanded_queries]}")

            # Step 2-4: Embed queries, search, and combine results
            logger.info("Step 2-4: Performing multi-query search and combining results...")
            combined_results = self._search_multi_query(
                expanded_queries, question
            )

            if not combined_results:
                logger.warning("No results found for any query variation")
                return []

            logger.info(
                f"Combined search returned {len(combined_results)} unique chunk(s)"
            )

            # Step 5: Optional reranking
            if self.use_reranking:
                logger.info("Step 5: Applying cross-encoder reranking...")
                combined_results = self._rerank_results(
                    question, combined_results
                )
                logger.info("Reranking completed successfully")
            else:
                logger.info("Step 5: Skipping reranking (disabled)")

            # Step 6: Return top-k
            logger.info(f"Step 6: Selecting top {self.top_k} results...")
            final_results = combined_results[: self.top_k]

            logger.info(
                f"Retrieval complete. Retrieved {len(final_results)} chunk(s)"
            )

            # Log retrieved chunks for debugging
            for i, (metadata, score) in enumerate(final_results):
                chunk_text = metadata.get('chunk_text', '').strip()
                if chunk_text:
                    text_preview = chunk_text[:100].replace('\n', ' ')
                    logger.debug(
                        f"Retrieved chunk {i+1}: score={score:.4f}, "
                        f"source='{metadata.get('source', 'unknown')}', "
                        f"page={metadata.get('page', 'unknown')} - '{text_preview}...'"
                    )
                else:
                    logger.warning(f"Retrieved chunk {i+1} has empty chunk_text: {metadata}")

            return final_results

        except Exception as e:
            logger.error(f"Error during retrieval: {str(e)}")
            raise Exception(f"Failed to retrieve chunks: {str(e)}") from e

    def _search_multi_query(
        self,
        queries: List[str],
        original_question: str,
    ) -> List[Tuple[dict, float]]:
        """Search vector store with multiple query variations.

        Combines results from all queries, deduplicating by chunk ID
        while preserving the best score for each chunk.

        Args:
            queries: List of query variations to search.
            original_question: Original user question (for logging).

        Returns:
            List of (metadata, score) tuples sorted by score (ascending).
        """
        combined_results_dict = {}  # chunk_id -> (metadata, best_score)

        for i, query in enumerate(queries, 1):
            try:
                logger.info(
                    f"Query {i}/{len(queries)}: Searching with '{query[:40]}...'"
                )

                # Embed query
                logger.debug(f"Query {i}: Embedding query...")
                query_embedding = self.embedding_service.encode([query])[0]

                # Search
                logger.debug(f"Query {i}: Performing vector similarity search...")
                results = self.vector_store.similarity_search_with_score(
                    query_embedding,
                    k=self.top_k * 2,  # Fetch extra to account for deduplication
                )
                logger.info(f"Query {i}: Found {len(results)} raw results")

                # Merge results, keeping best score per chunk
                logger.debug(f"Query {i}: Merging results with existing chunks...")
                for metadata, score in results:
                    # Use chunk_id as unique identifier if available
                    chunk_id = metadata.get("chunk_id", id(metadata))

                    if chunk_id not in combined_results_dict:
                        combined_results_dict[chunk_id] = (metadata, score)
                        logger.debug(f"Query {i}: Added new chunk {chunk_id} with score {score:.4f}")
                    else:
                        # Keep the lower score (better match)
                        existing_metadata, existing_score = combined_results_dict[
                            chunk_id
                        ]
                        if score < existing_score:
                            combined_results_dict[chunk_id] = (metadata, score)
                            logger.debug(f"Query {i}: Updated chunk {chunk_id} score from {existing_score:.4f} to {score:.4f}")

            except Exception as e:
                logger.warning(
                    f"Error searching with query {i}: {str(e)}. Continuing..."
                )
                continue

        # Convert to sorted list
        combined_results = sorted(
            combined_results_dict.values(),
            key=lambda x: x[1],
        )

        return combined_results

    def _rerank_results(
        self,
        question: str,
        results: List[Tuple[dict, float]],
    ) -> List[Tuple[dict, float]]:
        """Rerank results using cross-encoder.

        Args:
            question: User question.
            results: Combined search results.

        Returns:
            Reranked results sorted by cross-encoder score.
        """
        if not self.reranker or not results:
            return results

        try:
            # Extract text from metadata for reranking
            # Reconstruct chunk content from metadata if available
            candidate_texts = []
            for metadata, _ in results:
                # Try to get chunk content from metadata
                chunk_text = metadata.get("chunk_text", "")
                if not chunk_text:
                    # Fallback: construct snippet from metadata
                    chunk_text = f"{metadata.get('source', '')} (page {metadata.get('page', 'N/A')})"

                candidate_texts.append(chunk_text)

            logger.info(f"Reranking: Processing {len(candidate_texts)} candidate chunks")

            # Get reranked texts
            logger.debug("Reranking: Calling cross-encoder reranker...")
            reranked_texts = self.reranker.rerank(
                question,
                candidate_texts,
                top_k=len(results),
            )
            logger.info(f"Reranking: Cross-encoder returned {len(reranked_texts)} reranked results")

            # Map reranked texts back to original metadata
            # by matching text content
            reranked_results = []
            for ranked_text in reranked_texts:
                for idx, original_text in enumerate(candidate_texts):
                    if ranked_text == original_text:
                        metadata, original_score = results[idx]
                        reranked_results.append((metadata, original_score))
                        logger.debug(f"Reranking: Mapped result {idx+1} with original score {original_score:.4f}")
                        break

            logger.info(f"Reranking complete. Returned {len(reranked_results)} results in reranked order")

            return reranked_results

        except Exception as e:
            logger.warning(
                f"Error during reranking: {str(e)}. "
                f"Returning original results."
            )
            return results

    def get_config(self) -> dict:
        """Get retriever configuration.

        Returns:
            Dictionary with configuration parameters.
        """
        return {
            "use_reranking": self.use_reranking,
            "top_k": self.top_k,
            "num_query_variations": self.num_query_variations,
            "vector_store_size": self.vector_store.get_index_size(),
            "vector_dimension": self.vector_store.get_dimension(),
        }


def create_retriever(
    vector_store: FaissVectorStore,
    use_reranking: bool = True,
    top_k: int = 3,
) -> RetrieverService:
    """Factory function to create a RetrieverService.

    Args:
        vector_store: Built FaissVectorStore instance.
        use_reranking: Whether to use cross-encoder reranking.
        top_k: Number of top results to return.

    Returns:
        RetrieverService instance.
    """
    return RetrieverService(
        vector_store=vector_store,
        use_reranking=use_reranking,
        top_k=top_k,
    )
