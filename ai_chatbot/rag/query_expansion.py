"""Query expansion for improving search relevance.

Generates deterministic query variations without external APIs or LLMs.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Common phrases in system prompts and instructions to remove
PROMPT_PHRASES = {
    "answer the following",
    "respond to the following",
    "answer this question",
    "please answer",
    "provide an answer",
    "help me with",
    "can you",
    "could you",
    "would you",
    "what is",
    "explain",
    "describe",
    "tell me about",
    "what about",
}


def generate_dynamic_search_queries(question: str) -> List[str]:
    """Generate query variations for improved search coverage.

    Produces up to 5 deterministic query variants from a single question
    without using external LLMs or APIs.

    Args:
        question: Input question or query string.

    Returns:
        List of up to 5 unique query variations, with original question first.

    Raises:
        ValueError: If question is empty or invalid.
    """
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    question = question.strip()

    queries = []

    # 1. Original question
    queries.append(question)

    # 2. Cleaned version (remove prompt phrases)
    cleaned = _clean_question(question)
    if cleaned and cleaned != question:
        queries.append(cleaned)

    # 3. Keyword-based query (top 2 longest words)
    keyword_query = _extract_keyword_query(question)
    if keyword_query and keyword_query != question:
        queries.append(keyword_query)

    # 4. Remove punctuation version
    no_punct = _remove_punctuation(question)
    if no_punct and no_punct != question:
        queries.append(no_punct)

    # 5. Lowercase version (if significantly different)
    lowercase = question.lower()
    if lowercase != question and lowercase not in queries:
        queries.append(lowercase)

    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_normalized = q.strip().lower()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_queries.append(q)

    # Limit to 5 queries
    unique_queries = unique_queries[:5]

    logger.info(
        f"Generated {len(unique_queries)} query variation(s) from: '{question}'"
    )
    logger.debug(f"Query variations: {unique_queries}")

    return unique_queries


def _clean_question(question: str) -> str:
    """Remove common prompt phrases from question.

    Args:
        question: Input question string.

    Returns:
        Cleaned question with prompt phrases removed.
    """
    cleaned = question.lower()

    # Remove common prompt phrases
    for phrase in PROMPT_PHRASES:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Remove multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove leading/trailing punctuation
    cleaned = cleaned.strip(".,?!:;-'\"")

    return cleaned if cleaned else question


def _extract_keyword_query(question: str) -> str:
    """Extract keyword-based query from question.

    Extracts the 2 longest words (excluding common stop words)
    and combines them for a focused search query.

    Args:
        question: Input question string.

    Returns:
        Keyword-based query.
    """
    # Common English stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "be", "been", "was", "were",
        "that", "this", "these", "those", "what", "which", "who", "how", "why",
        "can", "could", "would", "should", "will", "shall", "do", "does", "did",
        "have", "has", "had", "as", "if", "it", "its", "you", "me", "him", "her",
    }

    # Extract words (alphanumeric sequences)
    words = re.findall(r"\b\w+\b", question.lower())

    # Filter out stop words and keep only words longer than 2 chars
    meaningful_words = [
        w for w in words
        if w not in stop_words and len(w) > 2
    ]

    # Get top 2 longest words
    if not meaningful_words:
        return question

    sorted_words = sorted(meaningful_words, key=len, reverse=True)
    top_keywords = sorted_words[:2]

    # Combine top keywords
    keyword_query = " ".join(top_keywords)

    return keyword_query if keyword_query else question


def _remove_punctuation(text: str) -> str:
    """Remove punctuation from text.

    Args:
        text: Input text string.

    Returns:
        Text with punctuation removed.
    """
    # Remove punctuation but keep spaces
    cleaned = re.sub(r"[^\w\s]", "", text)
    # Remove multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
