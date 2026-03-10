import logging
from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Message, ChatSession, ChatMessage
from .serializers import MessageSerializer, ChatRequestSerializer, ChatResponseSerializer
from ai_chatbot.rag.security import validate_user_input

logger = logging.getLogger(__name__)

# Initialize ChatService (to be injected from settings)
CHAT_SERVICE = None


def get_chat_service():
    """Get or initialize ChatService from Django settings."""
    global CHAT_SERVICE
    if CHAT_SERVICE is None:
        from django.conf import settings
        if hasattr(settings, 'CHAT_SERVICE'):
            CHAT_SERVICE = settings.CHAT_SERVICE
        else:
            logger.warning(
                "ChatService not configured in settings. "
                "Chat API will not work. Configure CHAT_SERVICE in settings.py"
            )
    return CHAT_SERVICE


class ChatAPIView(APIView):
    """API endpoint for RAG-based chat.

    POST /api/chat/
    Request: {"session_id": "...", "question": "..."}
    Response: {"answer": "...", "sources": [...], "similarity_scores": [...]}
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Handle chat request and return RAG-based answer.

        Args:
            request: HTTP request with session_id and question

        Returns:
            Response with answer, sources, and metadata
        """
        try:
            # Validate request data
            serializer = ChatRequestSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Invalid request data: {serializer.errors}")
                return Response(
                    {"error": "Invalid request", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            session_id = serializer.validated_data["session_id"]
            question = serializer.validated_data["question"]

            logger.info(f"Chat request: session={session_id}, question={question[:50]}...")

            # Security: Validate input for prompt injection
            is_valid, security_msg = validate_user_input(question)
            if not is_valid:
                logger.warning(f"Security block: {security_msg}")
                return Response(
                    {"error": "Request blocked for security reasons"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Get or create chat session
            try:
                session = ChatSession.objects.get(session_id=session_id)
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create(session_id=session_id)
                logger.info(f"Created new chat session: {session_id}")

            # Save user message
            user_message = ChatMessage.objects.create(
                session=session,
                role="user",
                content=question,
            )

            # Get ChatService and generate answer
            chat_service = get_chat_service()
            if chat_service is None:
                logger.error("ChatService not configured")
                return Response(
                    {"error": "Chat service not available"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # gather recent history for this session (ordered oldest->newest)
            history_msgs = ChatMessage.objects.filter(session=session).order_by("timestamp")
            history_list = [f"{msg.role}: {msg.content}" for msg in history_msgs]

            # Generate answer using RAG, rewriting question with history if present
            try:
                rag_response = chat_service.answer_question(question, history=history_list)
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return Response(
                    {"error": "Failed to generate answer"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Extract response data
            answer = rag_response.get("answer", "")
            citations = rag_response.get("citations", "")
            sources = rag_response.get("sources", [])
            similarity_scores = rag_response.get("similarity_scores", [])
            context_count = rag_response.get("context_count", 0)

            # Save assistant message (combine answer and citations for storage)
            combined_content = answer
            if citations:
                combined_content += f"\n\nCITATIONS:\n{citations}"

            top_score = similarity_scores[0] if similarity_scores else None
            top_page = None
            if sources and len(sources) > 0:
                top_page = sources[0].get("page")

            assistant_message = ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=combined_content,
                similarity_score=top_score,
                source_page=top_page,
            )

            logger.info(
                f"Generated answer. Sources: {context_count}, "
                f"Used fallback: {rag_response.get('used_fallback', False)}"
            )

            # Build response
            response_data = {
                "success": rag_response.get("success", True),
                "answer": answer,
                "citations": citations,
                "question": question,
                "sources": sources,
                "similarity_scores": similarity_scores,
                "context_count": context_count,
                "used_fallback": rag_response.get("used_fallback", False),
                "session_id": str(session.session_id),
                "message_id": assistant_message.id,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatHistoryAPIView(APIView):
    """API endpoint for retrieving chat history.

    GET /api/chat/history/?session_id=...
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Retrieve chat history for a session.

        Args:
            request: HTTP request with session_id query parameter

        Returns:
            List of messages in the chat session
        """
        try:
            session_id = request.query_params.get("session_id")
            if not session_id:
                return Response(
                    {"error": "session_id query parameter required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get chat session
            try:
                session = ChatSession.objects.get(session_id=session_id)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get all messages in session
            messages = ChatMessage.objects.filter(session=session).order_by("timestamp")

            messages_data = [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "similarity_score": msg.similarity_score,
                    "source_page": msg.source_page,
                }
                for msg in messages
            ]

            return Response(
                {
                    "session_id": str(session.session_id),
                    "created_at": session.created_at.isoformat(),
                    "messages": messages_data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by('-created_at')
    serializer_class = MessageSerializer
