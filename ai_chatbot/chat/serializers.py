from rest_framework import serializers
import uuid

from .models import Message, ChatSession, ChatMessage


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat API request."""
    session_id = serializers.UUIDField(required=False, allow_null=True)
    question = serializers.CharField(required=True, min_length=1, max_length=5000)
    
    def validate_session_id(self, value):
        """Auto-generate session_id if not provided."""
        if value is None:
            return uuid.uuid4()
        return value

    def validate_question(self, value):
        """Validate question is not empty after strip."""
        if not value.strip():
            raise serializers.ValidationError("Question cannot be empty")
        return value


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat API response."""
    success = serializers.BooleanField()
    answer = serializers.CharField()
    question = serializers.CharField()
    sources = serializers.ListField(child=serializers.DictField())
    similarity_scores = serializers.ListField(child=serializers.FloatField())
    context_count = serializers.IntegerField()
    used_fallback = serializers.BooleanField()
    session_id = serializers.UUIDField()
    message_id = serializers.IntegerField()


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ('session_id', 'created_at')


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'role', 'content', 'timestamp', 'similarity_score', 'source_page')
