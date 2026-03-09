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
        similarity_threshold: float = 0.3,  # Min cosine similarity to include result (higher = more restrictive)
    ):
        """Initialize the chat service.

        Args:
            retriever: Initialized RetrieverService instance.
            llm_service: LLM service (OpenAI, etc.) with generate() method.
            context_threshold: Minimum similarity to consider for LLM.
            min_keywords_in_context: Min question keywords required in context.
            similarity_threshold: Min cosine similarity to include result (higher = more restrictive).
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

            # DEDUPLICATION: Remove duplicate chunks
            logger.info(f"Retrieved {len(retrieved_chunks)} raw chunks, deduplicating...")
            deduplicated_chunks = self._deduplicate_chunks(retrieved_chunks)
            logger.info(f"After deduplication: {len(deduplicated_chunks)} unique chunks")

            if not deduplicated_chunks:
                logger.warning("No chunks after deduplication")
                return self._create_fallback_response(
                    question,
                    [],
                    [],
                    used_fallback=True,
                )

            # Filter chunks by similarity threshold
            filtered_chunks = [
                (metadata, score)
                for metadata, score in deduplicated_chunks
                if score >= self.similarity_threshold
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

            # RAG Step 2: Prepare context and validate
            logger.info("RAG Step 2: Preparing and validating context...")
            sources = [metadata for metadata, _ in filtered_chunks]
            scores = [score for _, score in filtered_chunks]

            # Combine context
            context = self._combine_context(sources)
            context_length = len(context.split()) if context.strip() else 0

            if not context.strip():
                logger.warning("Combined context is empty")
                return self._create_fallback_response(
                    question,
                    sources,
                    scores,
                    used_fallback=True,
                )

            logger.info(f"Combined context: {context_length} words from {len(sources)} sources")

            # RAG Step 3: Validate context before LLM
            logger.info("RAG Step 3: Validating context quality...")
            if not should_answer_with_llm(
                context,
                question,
                similarity_score=scores[0] if scores else None,
                similarity_threshold=self.context_threshold,
                min_keywords=self.min_keywords_in_context,
            ):
                logger.warning("Context validation failed - insufficient quality or relevance")
                return self._create_fallback_response(
                    question,
                    sources,
                    scores,
                    used_fallback=True,
                )

            logger.info("Context validation passed. Proceeding to LLM generation")

            # RAG Step 4: Build prompt
            logger.info("RAG Step 4: Building LLM prompt...")
            prompts = build_prompt(question, context)
            logger.debug(f"Built prompts: system ({len(prompts.get('system', ''))} chars), user ({len(prompts.get('user', ''))} chars)")

            # RAG Step 5: Call LLM with deterministic settings
            logger.info("RAG Step 5: Generating answer with LLM...")
            answer = self._call_llm_deterministic(
                question,
                context,
                prompts,
            )
            answer_length = len(answer.split()) if answer else 0
            logger.info(f"LLM generated answer: {answer_length} words")

            # RAG Step 6: Validate LLM answer for hallucinations
            logger.info("RAG Step 6: Validating LLM answer against context...")
            is_answer_valid = self._validate_llm_answer(answer, context, question)

            if not is_answer_valid:
                logger.warning("LLM answer failed validation (possible hallucination)")
                return self._create_fallback_response(
                    question,
                    sources,
                    scores,
                    used_fallback=True,
                )

            logger.info("LLM answer validation passed")

            # RAG Step 7: Create response
            logger.info("RAG Step 7: Creating final response...")
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

    def _deduplicate_chunks(
        self,
        chunks: List[Tuple[Dict[str, Any], float]],
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Remove duplicate chunks from retrieved results.

        Chunks are considered duplicates if they have the same chunk_text.
        When duplicates exist, keeps the one with better score.

        Args:
            chunks: List of (metadata, score) tuples.

        Returns:
            List of deduplicated (metadata, score) tuples.
        """
        seen_texts = {}  # chunk_text -> (metadata, score)

        for metadata, score in chunks:
            chunk_text = metadata.get("chunk_text", "").strip()

            if not chunk_text:
                logger.debug("Skipping chunk with empty text")
                continue

            # Use chunk_text as unique key
            if chunk_text not in seen_texts:
                seen_texts[chunk_text] = (metadata, score)
            else:
                # Keep chunk with better (lower) score
                existing_metadata, existing_score = seen_texts[chunk_text]
                if score < existing_score:
                    logger.debug(f"Replacing duplicate: score {existing_score:.4f} -> {score:.4f}")
                    seen_texts[chunk_text] = (metadata, score)

        deduplicated = list(seen_texts.values())
        logger.debug(f"Deduplication: {len(chunks)} -> {len(deduplicated)} chunks")

        return deduplicated

    def _validate_llm_answer(
        self,
        answer: str,
        context: str,
        question: str,
    ) -> bool:
        """Validate LLM answer against context for hallucinations.

        Performs basic sanity checks to detect suspicious responses:
        - Answer must not be empty or too short
        - Answer should not be ONLY the fallback message
        - Answer length should be reasonable relative to context
        - Citations should be present if answer is substantive

        Args:
            answer: LLM-generated answer (structured format).
            context: Retrieved context used for answering.
            question: Original user question.

        Returns:
            True if answer seems reasonable, False if suspicious.
        """
        if not answer or not isinstance(answer, str):
            logger.warning("Invalid answer for validation")
            return False

        answer_clean = answer.strip()

        # Check 1: Answer must have meaningful content (not just whitespace)
        if len(answer_clean) < 20:
            logger.warning(f"Answer too short: {len(answer_clean)} characters")
            return False

        # Check 2: Answer should not be ONLY the fallback message
        # (OK if fallback is part of a larger response, but not if it's the entire answer)
        fallback_msg = "This information is not present in the provided document."
        if answer_clean == fallback_msg:
            logger.warning("Answer is ONLY the fallback message")
            return False

        # Parse the structured response
        parsed_answer, parsed_citations = self._parse_llm_response(answer_clean)

        # Check 3: If there's a substantive answer, there should be citations
        if parsed_answer and len(parsed_answer.strip()) > 50:  # Substantive answer
            if not parsed_citations or len(parsed_citations.strip()) < 20:
                logger.warning("Substantive answer provided but citations are missing or too short")
                return False

        # Check 4: Sanity check on total length - answer shouldn't be unreasonably long
        answer_words = len(answer_clean.split())
        context_words = len(context.split())

        # Allow answer to be up to 5x context length (reasonable elaboration)
        if answer_words > context_words * 5:
            logger.warning(
                f"Answer suspiciously long: {answer_words} words vs {context_words} context words"
            )
            return False

        logger.debug(f"LLM answer validation passed - {answer_words} words, structured response with citations")
        return True

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
            logger.debug("LLM Call: Using deterministic settings (temperature=0.0, do_sample=False, max_tokens=500)")

            logger.debug(f"LLM Call: System prompt length: {len(prompts.get('system', ''))} characters")
            logger.debug(f"LLM Call: User prompt length: {len(prompts.get('user', ''))} characters")

            answer = self.llm_service.generate(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                temperature=0.0,  # Deterministic
                do_sample=False,  # No sampling
                max_tokens=500,
            )

            if not answer or not answer.strip():
                logger.warning("LLM returned empty or whitespace-only answer")
                return get_fallback_message()

            logger.info(f"LLM call successful. Answer length: {len(answer)} characters")
            return answer

        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            # Fallback to safe message
            return get_fallback_message()

    def _combine_context(self, sources: List[Dict[str, Any]]) -> str:
        """Combine multiple source chunks into single context with validation.

        Args:
            sources: List of metadata dicts.

        Returns:
            Combined context string.
        """
        contexts = []
        valid_sources = 0

        for idx, source in enumerate(sources, 1):
            # Try to get chunk content from metadata
            chunk_text = source.get("content", "")
            if not chunk_text:
                # Fallback: construct from metadata
                chunk_text = source.get("chunk_text", "")

            # Validate chunk_text
            if chunk_text and isinstance(chunk_text, str):
                cleaned_text = chunk_text.strip()
                if len(cleaned_text) >= 10:  # Minimum meaningful content
                    contexts.append(cleaned_text)
                    valid_sources += 1
                    logger.debug(f"Added valid chunk {idx}: {len(cleaned_text)} chars")
                else:
                    logger.warning(f"Skipping chunk {idx}: too short ({len(cleaned_text)} chars)")
            else:
                logger.warning(f"Skipping chunk {idx}: empty or invalid chunk_text")

        combined = "\n\n".join(contexts)

        if not combined.strip():
            logger.warning("Combined context is empty - no valid chunks found")
        else:
            logger.debug(
                f"Combined {valid_sources} valid source(s) into {len(combined)} chars"
            )

        return combined

    def _parse_llm_response(self, llm_response: str) -> Tuple[str, str]:
        """Parse structured LLM response into answer and citations.

        Expected format:
        ANSWER: [answer content]
        CITATIONS: [citation details]

        Args:
            llm_response: Raw LLM response string.

        Returns:
            Tuple of (answer, citations) strings.
        """
        if not llm_response or not isinstance(llm_response, str):
            logger.warning("Invalid LLM response for parsing")
            return "", ""

        response = llm_response.strip()

        # Look for ANSWER: marker
        answer_marker = "ANSWER:"
        citations_marker = "CITATIONS:"

        # Find positions
        answer_start = response.upper().find(answer_marker)
        citations_start = response.upper().find(citations_marker)

        if answer_start == -1:
            logger.warning("No ANSWER: marker found in LLM response")
            return response, ""  # Return whole response as answer

        # Extract answer section
        answer_start += len(answer_marker)
        if citations_start != -1:
            # Extract answer up to citations marker
            answer_text = response[answer_start:citations_start].strip()
        else:
            # No citations marker, take everything after ANSWER:
            answer_text = response[answer_start:].strip()

        # Extract citations section
        citations_text = ""
        if citations_start != -1:
            citations_start += len(citations_marker)
            citations_text = response[citations_start:].strip()

        logger.debug(f"Parsed response: answer ({len(answer_text)} chars), citations ({len(citations_text)} chars)")

        return answer_text, citations_text

    def _create_success_response(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        scores: List[float],
        context: str,
    ) -> Dict[str, Any]:
        """Create successful response with separated answer and citations.

        Args:
            question: User question.
            answer: Generated answer (structured with ANSWER: and CITATIONS:).
            sources: Source metadata.
            scores: Similarity scores.
            context: Combined context.

        Returns:
            Response dictionary with separated answer and citations.
        """
        # Parse the structured LLM response
        parsed_answer, parsed_citations = self._parse_llm_response(answer)

        return {
            "success": True,
            "answer": parsed_answer,
            "citations": parsed_citations,
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
            "citations": "",  # No citations for fallback responses
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
    similarity_threshold: float = 0.1,  # Lower threshold for better retrieval
) -> ChatService:
    """Factory function to create ChatService.

    Args:
        retriever: Initialized RetrieverService.
        llm_service: LLM service for generation.
        context_threshold: Minimum context similarity threshold.
        similarity_threshold: Minimum similarity for chunk filtering.

    Returns:
        ChatService instance.
    """
    return ChatService(
        retriever=retriever,
        llm_service=llm_service,
        context_threshold=context_threshold,
        similarity_threshold=similarity_threshold,
    )
