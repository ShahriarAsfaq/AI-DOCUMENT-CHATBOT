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
    system_prompt = """You are a document-based question answering system. Your ONLY responsibility is to answer questions using information explicitly stated in the provided document.

STRICT RULES - DO NOT BREAK THESE:

1. **USE ONLY THE PROVIDED DOCUMENT**: You must answer EXCLUSIVELY based on information present in the provided context document. No external knowledge. No training data. No inference beyond stated facts.

2. **STRUCTURED RESPONSE FORMAT**: Always respond in this exact format:
   ANSWER: [Your concise answer here]
   CITATIONS: [Detailed quotes and references from the document]

3. **QUOTE THE DOCUMENT**: In the CITATIONS section, you MUST include relevant excerpts from the document to show where the information comes from. Quote directly from the context.

4. **NO INFERENCE OR EXTRAPOLATION**: Do not infer, deduce, or extrapolate beyond what is explicitly written. Even if something seems reasonable or obvious, if it's not in the document, do not mention it.

5. **FALLBACK MESSAGE**: If the answer truly cannot be found in the provided document (even after careful reading), respond with EXACTLY:
   "This information is not present in the provided document."
   Do NOT guess, do NOT provide partial information.

6. **REASONABLE SUMMARIZATION**: You ARE allowed to reasonably summarize, paraphrase, or combine information from multiple places in the document - but only if the core facts are present.

7. **ACKNOWLEDGE AMBIGUITY**: If the context is unclear, contradictory, or incomplete regarding the answer, explicitly say so instead of making assumptions.

Your responses must be grounded entirely in the provided document. Every claim must be traceable back to the source document."""

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
===== BEGIN DOCUMENT =====
{context}
===== END DOCUMENT =====

QUESTION:
{question}

INSTRUCTIONS:
1. Use ONLY the information from the context document above
2. Respond in this exact format:
   ANSWER: [Your concise answer here]
   CITATIONS: [Detailed quotes and references from the document]
3. The ANSWER section should contain only the answer itself
4. The CITATIONS section should contain detailed quotes and references from the document
5. If the answer is not in the document, reply with: "{FALLBACK_MESSAGE}"
6. Do NOT use external knowledge, assumptions, or inferences
7. Do NOT provide partial answers if information is incomplete

IMPORTANT: If the answer can be reasonably inferred from the context, extract and summarize it.
Only use the fallback message if the document truly does not contain relevant information."""

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
