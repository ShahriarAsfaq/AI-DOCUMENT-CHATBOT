"""Hallucination guard to prevent LLM from generating false information.

Validates context quality before allowing LLM calls.
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Fallback message when context is insufficient
INSUFFICIENT_CONTEXT_MESSAGE = "This information is not present in the provided document."

# Common English stop words to exclude from keyword matching
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "be", "been", "was", "were",
    "that", "this", "these", "those", "what", "which", "who", "how", "why",
    "can", "could", "would", "should", "will", "shall", "do", "does", "did",
    "have", "has", "had", "as", "if", "it", "its", "you", "me", "him", "her",
}


def check_similarity_threshold(score: float, threshold: float = 0.65) -> Tuple[bool, str]:
    """Check if similarity score meets minimum threshold.

    Args:
        score: Similarity/relevance score (typically 0.0 to 1.0).
        threshold: Minimum acceptable score. Default: 0.65.

    Returns:
        Tuple of (is_valid, message) where:
        - is_valid: True if score >= threshold, False otherwise
        - message: Result message or fallback message

    Raises:
        ValueError: If score or threshold are invalid.
    """
    if not isinstance(score, (int, float)):
        raise ValueError("Score must be a number")

    if not isinstance(threshold, (int, float)):
        raise ValueError("Threshold must be a number")

    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")

    is_valid = score >= threshold

    logger.info(
        f"Similarity check: score={score:.4f}, threshold={threshold:.4f}, "
        f"valid={is_valid}"
    )

    if not is_valid:
        logger.warning(
            f"Similarity score ({score:.4f}) below threshold ({threshold:.4f}). "
            f"Context may not be relevant."
        )
        return False, INSUFFICIENT_CONTEXT_MESSAGE

    logger.info("Similarity score check passed")
    return True, "OK"


def validate_context_contains_keywords(
    context: str,
    question: str,
    min_keywords: int = 1,
) -> Tuple[bool, str]:
    """Validate that context contains meaningful keywords from question.

    Extracts key terms (non-stop words) from question and checks
    if they appear in the context.

    Args:
        context: Retrieved context/passage to validate.
        question: User question to extract keywords from.
        min_keywords: Minimum number of keywords that must appear in context.
                     Default: 1 (at least one keyword match required).

    Returns:
        Tuple of (is_valid, message) where:
        - is_valid: True if context contains enough keywords, False otherwise
        - message: Result message or fallback message

    Raises:
        ValueError: If context or question are invalid.
    """
    if not context or not isinstance(context, str):
        raise ValueError("Context must be a non-empty string")

    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    if min_keywords < 1:
        raise ValueError("min_keywords must be >= 1")

    # Extract keywords from question
    keywords = _extract_keywords(question)

    if not keywords:
        # If no meaningful keywords found, accept any context
        logger.debug("No meaningful keywords extracted from question")
        return True, "OK"

    # Check how many keywords appear in context (case-insensitive)
    context_lower = context.lower()
    matching_keywords = []

    for keyword in keywords:
        # Use word boundaries to match whole words
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, context_lower):
            matching_keywords.append(keyword)

    num_matches = len(matching_keywords)
    is_valid = num_matches >= min_keywords

    logger.info(
        f"Keyword validation: found {num_matches}/{len(keywords)} keywords "
        f"(required: {min_keywords}). Matching: {matching_keywords}"
    )

    if not is_valid:
        logger.warning(
            f"Context missing required keywords from question. "
            f"Found: {matching_keywords}, Required: {min_keywords}"
        )
        return False, INSUFFICIENT_CONTEXT_MESSAGE

    logger.info("Keyword validation passed")
    return True, "OK"


def validate_context_quality(
    context: str,
    question: str,
    similarity_score: float = None,
    similarity_threshold: float = 0.65,
    min_keywords: int = 1,
) -> Tuple[bool, str]:
    """Comprehensive context validation with flexible fallback logic.

    Uses AND logic for fallback: only rejects if BOTH similarity is poor AND
    no keywords match. Otherwise proceeds if either is good.

    Args:
        context: Retrieved context/passage to validate.
        question: User question.
        similarity_score: Optional similarity/relevance score (0.0-1.0).
        similarity_threshold: Minimum similarity score. Default: 0.65.
        min_keywords: Minimum keywords required in context. Default: 1.

    Returns:
        Tuple of (is_valid, message) where:
        - is_valid: True if context should be used (similarity >= threshold OR keywords match)
        - message: Result message

    Raises:
        ValueError: If inputs are invalid.
    """
    # Check similarity score
    similar_enough = True
    if similarity_score is not None:
        similar_enough = similarity_score >= similarity_threshold
        logger.info(
            f"Similarity check: score={similarity_score:.4f}, threshold={similarity_threshold:.4f}, "
            f"valid={similar_enough}"
        )
        if not similar_enough:
            logger.warning(
                f"Similarity score ({similarity_score:.4f}) below threshold ({similarity_threshold:.4f})"
            )

    # Check keywords in context
    keywords = _extract_keywords(question)
    keywords_match = True

    if keywords:
        context_lower = context.lower()
        matching_keywords = []

        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, context_lower):
                matching_keywords.append(keyword)

        keywords_match = len(matching_keywords) >= min_keywords

        logger.info(
            f"Keyword validation: found {len(matching_keywords)}/{len(keywords)} keywords "
            f"(required: {min_keywords}). Matching: {matching_keywords}"
        )

        if not keywords_match:
            logger.warning(
                f"Context missing required keywords. "
                f"Found: {matching_keywords}, Required: {min_keywords}"
            )
    else:
        logger.debug("No meaningful keywords extracted from question")

    # NEW LOGIC: Fallback only if BOTH similarity is bad AND no keywords match
    # Otherwise proceed if at least one is good
    should_answer = similar_enough or keywords_match

    if not should_answer:
        logger.warning("Failed validation: poor similarity AND no keyword matches")
        return False, INSUFFICIENT_CONTEXT_MESSAGE

    logger.info("Context validation passed (similarity good OR keywords match)")
    return True, "OK"


def should_answer_with_llm(
    context: str,
    question: str,
    similarity_score: float = None,
    similarity_threshold: float = 0.65,
    min_keywords: int = 1,
) -> bool:
    """Determine if context is sufficient to answer with LLM.

    Convenience function that returns a boolean for gating LLM calls.

    Args:
        context: Retrieved context/passage.
        question: User question.
        similarity_score: Optional similarity score.
        similarity_threshold: Minimum similarity threshold.
        min_keywords: Minimum keywords in context.

    Returns:
        True if context passes validation, False otherwise.
    """
    try:
        is_valid, _ = validate_context_quality(
            context,
            question,
            similarity_score,
            similarity_threshold,
            min_keywords,
        )
        return is_valid
    except ValueError:
        logger.error("Error validating context quality")
        return False


def _extract_keywords(question: str) -> List[str]:
    """Extract meaningful keywords from question.

    Removes stop words and returns content words.

    Args:
        question: Question string.

    Returns:
        List of meaningful keywords.
    """
    # Extract words (alphanumeric sequences)
    words = re.findall(r"\b\w+\b", question.lower())

    # Filter out stop words and short words
    keywords = [
        w for w in words
        if w not in STOP_WORDS and len(w) > 2
    ]

    return list(set(keywords))  # Remove duplicates
