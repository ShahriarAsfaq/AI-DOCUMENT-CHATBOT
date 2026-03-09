"""LLM service wrapper for generating answers.

Supports OpenAI or can be mocked for testing.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OpenAILLMService:
    """OpenAI-based LLM service for answer generation."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize OpenAI LLM service.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4)
        """
        self.api_key = api_key
        self.model = model

        try:
            import openai
            openai.api_key = api_key
            self.openai = openai
            logger.info(f"OpenAI LLM service initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {str(e)}")
            raise

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        do_sample: bool = False,
        max_tokens: int = 500,
    ) -> str:
        """Generate answer using OpenAI API.

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query with context
            temperature: Sampling temperature (0 = deterministic)
            do_sample: Whether to use sampling
            max_tokens: Maximum response tokens

        Returns:
            Generated response text
        """
        try:
            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            answer = response["choices"][0]["message"]["content"].strip()
            logger.debug("OpenAI response generated successfully")
            return answer

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise


class HuggingFaceLLMService:
    """HuggingFace-based LLM service for answer generation."""

    def __init__(self, token: str, model: str = "HuggingFaceH4/zephyr-7b-alpha"):
        """Initialize HuggingFace LLM service.

        Args:
            token: HuggingFace API token
            model: Model name (default: HuggingFaceH4/zephyr-7b-alpha)
        """
        self.token = token
        self.model = model

        try:
            from huggingface_hub import InferenceClient

            logger.info(f"Initializing HuggingFace Inference API for model: {model}")
            self.client = InferenceClient(
                model=model,
                token=token
            )
            logger.info(f"HuggingFace Inference API initialized successfully for: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace Inference API: {str(e)}")
            raise

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        do_sample: bool = False,
        max_tokens: int = 500,
    ) -> str:
        """Generate answer using HuggingFace model.

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query with context
            temperature: Sampling temperature (0 = deterministic)
            do_sample: Whether to use sampling
            max_tokens: Maximum response tokens

        Returns:
            Generated response text
        """
        try:
            # Format messages for chat API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            logger.debug(f"Calling HuggingFace Inference API with {len(user_prompt)} char context")

            # Call the inference API
            response = self.client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract the answer from response
            answer = response.choices[0].message.content.strip()

            logger.debug("HuggingFace Inference API response generated successfully")
            return answer

        except Exception as e:
            logger.error(f"Error calling HuggingFace Inference API: {str(e)}")
            raise


class GroqLLMService:
    """Groq-based LLM service using llama-3.1-8b-instant model."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        """Initialize Groq LLM service.

        Args:
            api_key: Groq API key
            model: Model name (default: llama-3.1-8b-instant)
        """
        self.api_key = api_key
        self.model = model

        try:
            from groq import Groq

            self.client = Groq(api_key=api_key)
            logger.info(f"Groq LLM service initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {str(e)}")
            raise

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        do_sample: bool = False,
        max_tokens: int = 500,
    ) -> str:
        """Generate answer using Groq API.

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query with context
            temperature: Sampling temperature (0 = deterministic)
            do_sample: Whether to use sampling
            max_tokens: Maximum response tokens

        Returns:
            Generated response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            answer = response.choices[0].message.content.strip()
            logger.debug("Groq response generated successfully")
            return answer

        except Exception as e:
            logger.error(f"Error calling Groq API: {str(e)}")
            raise


class MockLLMService:
    """Mock LLM service for testing without API calls."""

    def __init__(self):
        """Initialize mock LLM service."""
        logger.info("Using MockLLMService (no actual LLM calls)")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        do_sample: bool = False,
        max_tokens: int = 500,
    ) -> str:
        """Generate a mock answer.

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query with context
            temperature: Sampling temperature
            do_sample: Whether to use sampling
            max_tokens: Maximum response tokens

        Returns:
            Mock response text
        """
        # Extract context from user prompt if present
        if "CONTEXT DOCUMENT:" in user_prompt:
            parts = user_prompt.split("CONTEXT DOCUMENT:")
            if len(parts) > 1:
                context = parts[1].split("QUESTION:")[0].strip()
                # Return a simple response based on context
                context_preview = context[:100]
                return f"Based on the provided context: {context_preview}... This demonstrates the mock LLM service is working correctly."

        return "Mock LLM response: The system is operational and ready to process queries."