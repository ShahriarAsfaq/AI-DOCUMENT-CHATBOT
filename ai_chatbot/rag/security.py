"""Security module for detecting and preventing prompt injection attacks.

Identifies malicious prompts attempting to override system instructions.
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Prompt injection patterns to detect
INJECTION_PATTERNS = [
    # Ignore instructions
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "forget previous instructions",

    # Act as different entity
    "act as system",
    "act as admin",
    "act as root",
    "pretend you are",
    "pretend that you are",
    "you are now",

    # Reveal system information
    "reveal system prompt",
    "show system prompt",
    "what is your system prompt",
    "tell me your system prompt",
    "what is your prompt",
    "show your instructions",
    "reveal instructions",

    # Override rules
    "override rules",
    "override all rules",
    "bypass rules",
    "ignore safety",
    "ignore guardrails",
    "ignore restrictions",
    "there are no restrictions",

    # Jailbreak attempts
    "jailbreak",
    "jailbroken",
    "you are being jailbroken",

    # SQL injection-like patterns
    "'; drop",
    "-- ",
    "1=1",

    # Role switching
    "switch mode",
    "switch to",
    "activate mode",
    "enable mode",
]

# Suspicious keywords that may require additional scrutiny
SUSPICIOUS_KEYWORDS = [
    "system prompt",
    "instructions",
    "constraints",
    "rules",
    "restrictions",
    "guardrails",
    "safety",
]


def detect_prompt_injection(question: str) -> Tuple[bool, List[str]]:
    """Detect prompt injection attacks in user input.

    Checks for common patterns used to override system instructions
    or reveal internal prompts.

    Args:
        question: User input to check for injection attempts.

    Returns:
        Tuple of (is_injection, detected_patterns) where:
        - is_injection: True if injection patterns detected
        - detected_patterns: List of detected injection patterns

    Raises:
        ValueError: If question is invalid.
    """
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    question_lower = question.lower()
    detected = []

    # Check for exact pattern matches
    for pattern in INJECTION_PATTERNS:
        if pattern in question_lower:
            detected.append(pattern)
            logger.warning(
                f"Prompt injection detected: '{pattern}' in input"
            )

    is_injection = len(detected) > 0

    if is_injection:
        logger.critical(
            f"SECURITY ALERT: Prompt injection attempt detected. "
            f"Patterns: {detected}. Input: '{question[:100]}...'"
        )

    return is_injection, detected


def validate_user_input(question: str) -> Tuple[bool, str]:
    """Validate user input for security threats.

    Performs multiple security checks and returns a decision.

    Args:
        question: User question to validate.

    Returns:
        Tuple of (is_valid, message) where:
        - is_valid: True if input is safe, False if blocked
        - message: Reason message

    Raises:
        ValueError: If question is invalid.
    """
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    # Check for prompt injection
    is_injection, patterns = detect_prompt_injection(question)

    if is_injection:
        logger.warning(f"Input validation failed: injection detected")
        return False, f"Blocked: Detected suspicious patterns: {', '.join(patterns)}"

    # Check for extremely long inputs (potential DoS)
    max_length = 5000
    if len(question) > max_length:
        logger.warning(f"Input validation failed: exceeds max length")
        return False, f"Input exceeds maximum length ({max_length} characters)"

    # Check for null bytes or other control characters
    if any(ord(c) < 32 and c not in '\n\t\r' for c in question):
        logger.warning("Input validation failed: contains control characters")
        return False, "Input contains invalid control characters"

    logger.debug("Input validation passed")
    return True, "OK"


def sanitize_logging_input(text: str, max_length: int = 200) -> str:
    """Sanitize user input for safe logging.

    Prevents logging of potentially sensitive data.

    Args:
        text: Text to sanitize for logging.
        max_length: Maximum length to keep.

    Returns:
        Sanitized text safe for logging.
    """
    if not text:
        return ""

    # Truncate
    truncated = text[:max_length]

    # Remove newlines for single-line logging
    sanitized = truncated.replace('\n', ' ').replace('\r', ' ')

    # Remove potential sensitive keywords
    for keyword in SUSPICIOUS_KEYWORDS:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        sanitized = pattern.sub("[REDACTED]", sanitized)

    return sanitized


def block_request_if_injection(question: str) -> None:
    """Raise exception if prompt injection detected.

    Used as a middleware/decorator check for blocking requests.

    Args:
        question: User question to validate.

    Raises:
        PermissionError: If injection detected.
        ValueError: If question is invalid.
    """
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")

    is_injection, patterns = detect_prompt_injection(question)

    if is_injection:
        logger.critical(
            f"REQUEST BLOCKED: Prompt injection attempt. "
            f"Detected: {patterns}"
        )
        raise PermissionError(
            f"Your request has been blocked for security reasons. "
            f"Detected suspicious patterns: {', '.join(patterns[:3])}"
        )


class SecurityValidator:
    """Reusable security validator for requests.

    Can be used as a decorator or called directly.
    """

    def __init__(self, raise_on_injection: bool = True):
        """Initialize validator.

        Args:
            raise_on_injection: Whether to raise PermissionError on injection.
        """
        self.raise_on_injection = raise_on_injection

    def validate(self, question: str) -> Tuple[bool, str]:
        """Validate user input.

        Args:
            question: User question.

        Returns:
            Tuple of (is_valid, message).

        Raises:
            PermissionError: If injection detected and raise_on_injection=True.
        """
        is_valid, message = validate_user_input(question)

        if not is_valid and self.raise_on_injection:
            raise PermissionError(message)

        return is_valid, message

    def __call__(self, question: str) -> Tuple[bool, str]:
        """Allow use as callable.

        Args:
            question: User question.

        Returns:
            Tuple of (is_valid, message).
        """
        return self.validate(question)


# Convenience instances
security_validator = SecurityValidator(raise_on_injection=True)
security_checker = SecurityValidator(raise_on_injection=False)
