from rest_framework import viewsets, status
from rest_framework.response import Response
import os
from django.conf import settings
from django.core.management import call_command
from pathlib import Path

from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('-uploaded_at')
    serializer_class = DocumentSerializer

    def create(self, request, *args, **kwargs):
        """Override create to ensure only one document exists at a time.

        When uploading a new document, delete all existing documents
        and their files from the filesystem.
        """
        # Delete all existing documents and their files
        existing_documents = Document.objects.all()
        for doc in existing_documents:
            # Delete the file from filesystem
            file_path = os.path.join(settings.MEDIA_ROOT, doc.file.name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    # Log the error but continue
                    print(f"Warning: Could not delete file {file_path}: {e}")

            # Delete the document from database
            doc.delete()

        # Now create the new document
        response = super().create(request, *args, **kwargs)

        # If document creation was successful, process it to rebuild vector store
        if response.status_code == status.HTTP_201_CREATED:
            try:
                print("Processing new document to rebuild vector store...")
                call_command('process_documents')
                print("Vector store rebuilt successfully")

                # Reload the vector store in the chat service
                try:
                    from ai_chatbot.chat.views import get_chat_service
                    chat_service = get_chat_service()
                    if chat_service and hasattr(chat_service, 'retriever') and hasattr(chat_service.retriever, 'vector_store'):
                        processed_store_path = Path(settings.VECTOR_STORE_PATH) / "faiss_store"
                        chat_service.retriever.vector_store.reload_index(str(processed_store_path))
                        print("Vector store reloaded in chat service")
                except Exception as reload_error:
                    print(f"Warning: Failed to reload vector store in chat service: {reload_error}")

            except Exception as e:
                print(f"Warning: Failed to process document: {e}")
                # Don't fail the upload if processing fails

        return response
