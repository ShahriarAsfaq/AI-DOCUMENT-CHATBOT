"""Prompt building for controlled LLM responses.

Constructs system and user prompts designed to prevent hallucination
and enforce context-only answering.
"""

import logging

logger = logging.getLogger(__name__)

# Exact fallback message that LLM must use if answer not in context
FALLBACK_MESSAGE = "This information is not present in the provided document."


def build_prompt(question: str, context: str) -> dict:
    """Build system and user prompts for context-constrained answering.

    Constructs prompts that strictly instruct the model to:
    - Answer ONLY based on provided context
    - Use exact fallback message if answer not found
    - Avoid guessing, inference, or external knowledge
    - Refuse to extrapolate beyond context

    Args:
        question: User's question or query.
        context: Retrieved context/document passage to use as knowledge source.

    Returns:
        Dictionary with 'system' and 'user' keys containing prompt strings.

    Raises:
        ValueError: If question or context are empty.
    """
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    if not context or not isinstance(context, str):
        raise ValueError("Context must be a non-empty string")

    logger.info(
        f"Building prompt for question: '{question[:50]}...' "
        f"with context length: {len(context)} chars"
    )

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(question, context)

    prompt_dict = {
        "system": system_prompt,
        "user": user_prompt,
    }

    logger.debug(f"Prompt built successfully. System prompt length: {len(system_prompt)}")

    return prompt_dict


def build_full_prompt(question: str, context: str) -> str:
    """Build a single concatenated prompt string.

    Combines system and user prompts into a single string format.
    Useful for models that don't support separate system prompts.

    Args:
        question: User's question or query.
        context: Retrieved context/document passage.

    Returns:
        Single prompt string with system and user sections.

    Raises:
        ValueError: If question or context are empty.
    """
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    if not context or not isinstance(context, str):
        raise ValueError("Context must be a non-empty string")

    prompt_dict = build_prompt(question, context)

    full_prompt = f"{prompt_dict['system']}\n\n{prompt_dict['user']}"

    logger.debug("Full prompt built successfully")

    return full_prompt


def _build_system_prompt() -> str:
    """Build the system prompt for context-only answering.

    Returns:
        System prompt string.
    """
    system_prompt = """You are a helpful assistant that answers questions STRICTLY based on the provided context document.

CRITICAL RULES:
1. Answer ONLY based on information present in the provided context
2. Do NOT use external knowledge, training data, or inference
3. Do NOT guess, infer, or extrapolate beyond what is explicitly stated
4. If the answer is not found in the context, respond with EXACTLY:
   "This information is not present in the provided document."
5. Be precise and factual - quote or closely paraphrase the context
6. If the context is unclear or contradictory, acknowledge the ambiguity
7. NEVER make up information or assume knowledge not in the context

Your responses must be deterministic and grounded only in the provided document."""

    return system_prompt


def _build_user_prompt(question: str, context: str) -> str:
    """Build the user prompt with question and context.

    Args:
        question: User's question.
        context: Retrieved context passage.

    Returns:
        User prompt string.
    """
    user_prompt = f"""CONTEXT DOCUMENT:
{context}

QUESTION:
{question}

INSTRUCTIONS:
- Answer based ONLY on the above context document
- If the answer is not in the context, reply with: "{FALLBACK_MESSAGE}"
- Do not use external knowledge
- Do not infer beyond stated facts
- Be direct and concise"""

    return user_prompt


def get_fallback_message() -> str:
    """Get the exact fallback message for insufficient context.

    Returns:
        Fallback message string.
    """
    return FALLBACK_MESSAGE


def is_LLM_response_valid(response: str, context: str) -> bool:
    """Check if LLM response adheres to context constraints (basic heuristic).

    This is a simple heuristic check - not a guarantee.
    Real validation requires semantic understanding.

    Args:
        response: LLM's response string.
        context: Original context provided to LLM.

    Returns:
        True if response contains keywords from context or is fallback message.
        False if response appears to use external knowledge.

    Note:
        This is a best-effort heuristic and may have false positives/negatives.
    """
    response_lower = response.lower()

    # Check if response is the fallback message
    if response_lower.strip() == FALLBACK_MESSAGE.lower():
        return True

    # Basic check: does response share significant vocabulary with context?
    context_words = set(
        word.lower() for word in context.split() if len(word) > 3
    )
    response_words = set(
        word.lower() for word in response.split() if len(word) > 3
    )

    # If response shares at least some vocabulary with context, it's likely grounded
    overlap = len(context_words & response_words)

    # Low threshold - just looking for some connection to context
    min_overlap = 2

    is_valid = overlap >= min_overlap

    logger.debug(
        f"LLM response validation: overlap={overlap}, valid={is_valid}"
    )

    return is_valid
