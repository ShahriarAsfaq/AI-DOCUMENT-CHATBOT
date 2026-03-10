#!/usr/bin/env python
"""Test script for the RAG pipeline."""

import os
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_chatbot.settings')
django.setup()

from ai_chatbot.settings import get_or_create_chat_service

def test_rag_pipeline():
    """Test the RAG pipeline with a sample question."""

    print("Testing RAG Pipeline...")

    # Get the chat service
    chat_service = get_or_create_chat_service()

    if not chat_service:
        print("FAILED: Chat service not available")
        return

    print("SUCCESS: Chat service initialized")

    # Test question
    # 1. regular question to verify retrieval
    question = "What is the technical test about?"
    print(f"\nQUESTION: {question}")

    try:
        result = chat_service.answer_question(question)

        answer = result.get("answer", "No answer")
        sources = result.get("sources", [])
        context = result.get("context", "")
        used_fallback = result.get("used_fallback", True)

        print(f"\nANSWER: {answer[:200]}...")
        print(f"SOURCES: {len(sources)} chunks")
        print(f"CONTEXT_LENGTH: {len(context)} characters")
        print(f"USED_FALLBACK: {used_fallback}")

        if not used_fallback and sources:
            print("\nSUCCESS: RAG system answered using retrieved context!")
            print("\nSample source chunks:")
            for i, source in enumerate(sources[:2]):  # Show first 2 sources
                chunk_text = source.get('chunk_text', '')[:100]
                print(f"  {i+1}. Page {source.get('page', '?')}: '{chunk_text}...'")
        else:
            print("\nFAILED: System fell back or no sources found")

    except Exception as e:
        print(f"FAILED: Error testing RAG pipeline: {str(e)}")
        import traceback
        traceback.print_exc()

    # 2. test summary intent
    question = "Please summarize the document."
    print(f"\nQUESTION (summary intent): {question}")
    try:
        result = chat_service.answer_question(question)
        print(f"ANSWER: {result.get('answer')}")
        print(f"CITATIONS: {result.get('citations')}")
    except Exception as e:
        print(f"ERROR in summary intent: {e}")

    # 3. test topic count/list intents
    question = "How many topics are covered?"
    print(f"\nQUESTION (topic count intent): {question}")
    try:
        result = chat_service.answer_question(question)
        print(f"ANSWER: {result.get('answer')}")
        print(f"CITATIONS: {result.get('citations')}")
    except Exception as e:
        print(f"ERROR in topic count intent: {e}")

    question = "What are the main topics?"
    print(f"\nQUESTION (topic list intent): {question}")
    try:
        result = chat_service.answer_question(question)
        print(f"ANSWER: {result.get('answer')}")
        print(f"CITATIONS: {result.get('citations')}")
    except Exception as e:
        print(f"ERROR in topic list intent: {e}")

    # 4. test rewriting with conversation history
    history = [
        "user: What was the first chapter about?",
        "assistant: It introduced microfinance principles and definitions.",
        "user: And the second chapter?"
    ]
    question = "Tell me more about the regulations?"
    print(f"\nQUESTION (with history): {question}")
    try:
        result = chat_service.answer_question(question, history=history)
        print(f"REWRITTEN ANSWER: {result.get('answer')}")
        print(f"CITATIONS: {result.get('citations')}")
    except Exception as e:
        print(f"ERROR in history rewrite: {e}")

if __name__ == "__main__":
    test_rag_pipeline()