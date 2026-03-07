"""Chat service for answering questions using RAG.

Orchestrates retrieval, validation, prompt building, and LLM calls.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any

from ai_chatbot.rag.retriever import RetrieverService
from ai_chatbot.rag.prompt_builder import (
    build_prompt,
    get_fallback_message,
)
from ai_chatbot.rag.hallucination_guard import (
    should_answer_with_llm,
    INSUFFICIENT_CONTEXT_MESSAGE,
)

logger = logging.getLogger(__name__)


class ChatService:
    """Service for answering questions using RAG with LLM.

    Combines retrieval, validation, prompt building, and LLM generation
    to produce grounded, factual answers.
    """

    def __init__(
        self,
        retriever: RetrieverService,
        llm_service,  # OpenAI or similar service
        context_threshold: float = 0.65,
        min_keywords_in_context: int = 1,
        similarity_threshold: float = 0.5,  # For deduplication check
    ):
        """Initialize the chat service.

        Args:
            retriever: Initialized RetrieverService instance.
            llm_service: LLM service (OpenAI, etc.) with generate() method.
            context_threshold: Minimum similarity to consider for LLM.
            min_keywords_in_context: Min question keywords required in context.
            similarity_threshold: Min similarity score to include result.
        """
        self.retriever = retriever
        self.llm_service = llm_service
        self.context_threshold = context_threshold
        self.min_keywords_in_context = min_keywords_in_context
        self.similarity_threshold = similarity_threshold

        logger.info(
            f"ChatService initialized. "
            f"Context threshold: {context_threshold}, "
            f"Min keywords: {min_keywords_in_context}"
        )

    def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer a question using RAG with LLM.

        Pipeline:
        1. Retrieve relevant chunks using RetrieverService
        2. Validate context quality
        3. Build deterministic prompt
        4. Call LLM with deterministic settings (temp=0, do_sample=False)
        5. Return answer with sources and metadata

        Args:
            question: User's question.

        Returns:
            Dictionary with:
            - 'answer': Generated answer string
            - 'sources': List of source metadata dicts
            - 'similarity_scores': List of similarity scores
            - 'context_count': Number of chunks used
            - 'used_fallback': Boolean indicating if fallback was used

        Raises:
            ValueError: If question is invalid.
            Exception: For processing failures.
        """
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")

        try:
            logger.info(f"Processing question: '{question[:60]}...'")

            # Step 1: Retrieve relevant chunks
            retrieved_chunks = self.retriever.retrieve(question)

            if not retrieved_chunks:
                logger.warning("No chunks retrieved for question")
                return self._create_fallback_response(
                    question,
                    [],
                    [],
                    used_fallback=True,
                )

            # Filter chunks by similarity threshold
            filtered_chunks = [
                (metadata, score)
                for metadata, score in retrieved_chunks
                if score <= self.similarity_threshold
            ]

            if not filtered_chunks:
                logger.warning(
                    f"No chunks passed similarity threshold "
                    f"({self.similarity_threshold})"
                )
                return self._create_fallback_response(
                    question,
                    [],
                    [],
                    used_fallback=True,
                )

            logger.info(
                f"Retrieved {len(filtered_chunks)} chunk(s) after filtering"
            )

            # Step 2: Prepare context and validate
            sources = [metadata for metadata, _ in filtered_chunks]
            scores = [score for _, score in filtered_chunks]

            # Combine context
            context = self._combine_context(sources)

            if not context.strip():
                logger.warning("Combined context is empty")
                return self._create_fallback_response(
                    question,
                    sources,
                    scores,
                    used_fallback=True,
                )

            # Step 3: Validate context before LLM
            if not should_answer_with_llm(
                context,
                question,
                similarity_score=scores[0] if scores else None,
                similarity_threshold=self.context_threshold,
                min_keywords=self.min_keywords_in_context,
            ):
                logger.warning("Context validation failed")
                return self._create_fallback_response(
                    question,
                    sources,
                    scores,
                    used_fallback=True,
                )

            logger.info("Context validation passed. Proceeding to LLM")

            # Step 4: Build prompt
            prompts = build_prompt(question, context)

            # Step 5: Call LLM with deterministic settings
            logger.debug("Calling LLM with deterministic settings")
            answer = self._call_llm_deterministic(
                question,
                context,
                prompts,
            )

            # Step 6: Create response
            return self._create_success_response(
                question=question,
                answer=answer,
                sources=sources,
                scores=scores,
                context=context,
            )

        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            raise Exception(f"Failed to answer question: {str(e)}") from e

    def _call_llm_deterministic(
        self,
        question: str,
        context: str,
        prompts: Dict[str, str],
    ) -> str:
        """Call LLM with deterministic settings.

        Args:
            question: User question.
            context: Retrieved context.
            prompts: Dictionary with 'system' and 'user' prompts.

        Returns:
            LLM-generated answer.
        """
        try:
            # Deterministic settings: temperature=0, do_sample=False
            logger.debug("Calling LLM with temperature=0, do_sample=False")

            answer = self.llm_service.generate(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                temperature=0.0,  # Deterministic
                do_sample=False,  # No sampling
                max_tokens=500,
            )

            if not answer or not answer.strip():
                logger.warning("LLM returned empty answer")
                return get_fallback_message()

            logger.info("LLM generated answer successfully")
            return answer

        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            # Fallback to safe message
            return get_fallback_message()

    def _combine_context(self, sources: List[Dict[str, Any]]) -> str:
        """Combine multiple source chunks into single context.

        Args:
            sources: List of metadata dicts.

        Returns:
            Combined context string.
        """
        contexts = []

        for idx, source in enumerate(sources, 1):
            # Try to get chunk content from metadata
            chunk_text = source.get("content", "")
            if not chunk_text:
                # Fallback: construct from metadata
                chunk_text = source.get("chunk_text", "")

            if chunk_text:
                contexts.append(chunk_text)
        
        combined = "\n\n".join(contexts)
        logger.debug(
            f"Combined {len(sources)} source(s) into {len(combined)} chars"
        )

        return combined

    def _create_success_response(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        scores: List[float],
        context: str,
    ) -> Dict[str, Any]:
        """Create successful response.

        Args:
            question: User question.
            answer: Generated answer.
            sources: Source metadata.
            scores: Similarity scores.
            context: Combined context.

        Returns:
            Response dictionary.
        """
        return {
            "success": True,
            "answer": answer,
            "question": question,
            "sources": sources,
            "similarity_scores": scores,
            "context_count": len(sources),
            "used_fallback": False,
        }

    def _create_fallback_response(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        scores: List[float],
        used_fallback: bool = True,
    ) -> Dict[str, Any]:
        """Create fallback response.

        Args:
            question: User question.
            sources: Source metadata (may be empty).
            scores: Similarity scores (may be empty).
            used_fallback: Whether fallback was used.

        Returns:
            Response dictionary with fallback message.
        """
        return {
            "success": False,
            "answer": INSUFFICIENT_CONTEXT_MESSAGE,
            "question": question,
            "sources": sources,
            "similarity_scores": scores,
            "context_count": len(sources),
            "used_fallback": used_fallback,
        }

    def get_config(self) -> Dict[str, Any]:
        """Get chat service configuration.

        Returns:
            Configuration dictionary.
        """
        return {
            "context_threshold": self.context_threshold,
            "min_keywords_in_context": self.min_keywords_in_context,
            "similarity_threshold": self.similarity_threshold,
            "retriever_config": self.retriever.get_config(),
        }


def create_chat_service(
    retriever: RetrieverService,
    llm_service,
    context_threshold: float = 0.65,
) -> ChatService:
    """Factory function to create ChatService.

    Args:
        retriever: Initialized RetrieverService.
        llm_service: LLM service for generation.
        context_threshold: Minimum context similarity threshold.

    Returns:
        ChatService instance.
    """
    return ChatService(
        retriever=retriever,
        llm_service=llm_service,
        context_threshold=context_threshold,
    )
